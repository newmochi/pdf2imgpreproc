"""
======================================================================
Project Name    : PDFイメージ前処理発掘調査
Program Name    : PDFイメージ矩形取得プログラム
File Name       : pdf2imgpreproc.py
Encoding        : utf-8
Creation Date   : 2020.9.12
Creation User   : Hiroyuki.Mochizuki

Copyright c 2020 Hiroyuki Mochizuki (holiday programmer)

This source code or any portion thereof must not be
reproduced or used in any manner whatsoever.
======================================================================
    Arguments
    ----------
    arg1: 入力PDFフォルダ(./folder または ../xx/yy/folder 等/区切り)
    arg2: JPEG出力フォルダ名out( out/folder/...とJPEGが出力される)
    --log WARN がデフォルト値
    --log INFO とすれば本プログラムでのINFOが出る。(実質デバッグ情報)
    --log DEBUG とするとライブラリ含めてデバッグがいっぱい出てしまう。
    ----------
    need to run
    ----------
    fm_img_preprocs.py
    config_pdf2imgpreproc.ini
    ----------
"""
import datetime
from pathlib import Path
import pdf2image
import cv2
import numpy as np
import glob
import argparse
import os
import sys
import errno
from PIL import Image
import configparser # for ini
import re # for globでreを使う。

# log汎用系main配置01
# https://qiita.com/SatoshiTerasaki/items/f16a4cfacb83039450fd
import logging
LOG_LEVEL = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']
USER_CHOICE = LOG_LEVEL+list(map(lambda w: w.lower(), LOG_LEVEL))
# 別のファイルでは以下2行
# import logging
# logger = logging.getLogger(__name__)
# def xx():


# 各種初期値
mod_flag = 1 # fmで始まる関数をコールしたら実際にイメージが変わる
points_array = []
extract_PILimages = []
out_PILimages = []

# import fm_img_preprocs
from fm_img_preprocs import fm_draw_rec
from fm_img_preprocs import fm_mod_degree
from fm_img_preprocs import fm_extract_1table
from fm_img_preprocs import fm_draw_recandlines

# Arg処理
# 例 入力フォルダ名 : "xxx/1882"
#    出力フォルダ名 : "out"
#    出力フォルダは、out/1882/ファイル名拡張子抜いたもの/ページごとのjpgファイル
#    --log でログレベル

parser = argparse.ArgumentParser (description= \
    'python tp12_t08_image.py 入力folder(PDFファイル複数) 出力folder(入力folder+ファイルごとfolder)')

# Arg処理：parser.add_argumentで受け取る引数を追加していく
parser.add_argument('arg1',
    help='入力フォルダ名(階層不可、配下に複数PDFファイル)')    # 必須の引数を追加
parser.add_argument('arg2',
    help='出力フォルダ名(この配下に入力フォルダ名＋PDFファイル名のフォルダ作成)')
# log汎用系main配置02
parser.add_argument("--log", help='set log level',
                    choices=USER_CHOICE,
                    default="WARN")

args = parser.parse_args()

tmpstr = args.arg1
out_dir0 = args.arg2

# log汎用系main配置03
numeric_level = getattr(logging, args.log.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % loglevel)
logging.basicConfig(level=numeric_level)
logger = logging.getLogger("tp12_t08_pdf2imgpreproc")
# あとは、logger.debug("文字列")
# あとは、logger.info("文字列")
# あとは、logger.warn("文字列")
# あとは、logger.error("文字列")
# あとは、logger.critical("文字列")

in_dir = tmpstr
if '\\' in in_dir:
    print('お手数ですがフォルダ区切りは、スラッシュで指定ください')
    sys.exit()

if '/' in in_dir:
    lastfolder = in_dir.rsplit('/', 1)[1]
else:
    lastfolder = in_dir
out_dir1 = out_dir0 + '/' + lastfolder


# config_pdf2imgpreproc.ini読込

config_ini = configparser.ConfigParser()
config_ini_path = 'config_pdf2imgpreproc.ini'

if not os.path.exists(config_ini_path):
    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), config_ini_path)

config_ini.read(config_ini_path, encoding='utf-8')

read_ini = config_ini['parameter']

# 本来は以下を1つ1つ行うべきだが、intへの代入時nullならセットにした
# if "dpi" in map(lambda x:x[0], inifile.items("parameter")):
ini_dpi = read_ini.get('dpi')
ini_quality = read_ini.get('quality')
ini_draw_rec_thick = read_ini.get('draw_rec_thick')
ini_draw_line_thick = read_ini.get('draw_line_thick')

# 以下はオペに影響するので指定がないときはエラーとする
ini_extract_1table_on = read_ini.get('extract_1table_on')
ini_mod_degree_on = read_ini.get('mod_degree_on')
ini_draw_rec_on = read_ini.get('draw_rec_on')
ini_draw_recandlines_on = read_ini.get('draw_recandlines_on')
if ini_extract_1table_on is None:
    print("extract_1table_onは必須パラメータです(config_pdf2imagpreproc.ini)。")
    sys.exit(1)
if ini_mod_degree_on is None:
    print("mod_degree_onは必須パラメータです(config_pdf2imagpreproc.ini)。")
    sys.exit(1)
if ini_draw_rec_on is None:
    print("draw_rec_onは必須パラメータです(config_pdf2imagpreproc.ini)。")
    sys.exit(1)
if ini_draw_recandlines_on is None:
    print("draw_recandlines_onは必須パラメータです(config_pdf2imagpreproc.ini)。")
    sys.exit(1)

# sharpness_on = read_ini.get('sharpness_on')

convdpi = int(ini_dpi) if ini_dpi is not None else 400
convquality = int(ini_quality) if ini_quality is not None else 90
draw_rec_thick = int(ini_draw_rec_thick) if ini_draw_rec_thick is not None else 10
draw_line_thick = int(ini_draw_line_thick) if ini_draw_line_thick is not None else 2

extract_1table_on = int(ini_extract_1table_on)
mod_degree_on = int(ini_mod_degree_on)
draw_rec_on = int(ini_draw_rec_on)
draw_recandlines_on = int(ini_draw_recandlines_on)

# iniファイルでの不整合を強制的に修正。
# 不整合1:draw_recとdraw_reclineどちらも1はプログラム終了
# 理由：無駄なだけでなく、コード上どちらも出力用リストに入れているため。
if draw_rec_on ==1 and draw_recandlines_on == 1:
    print("pdf2imgproc.iniを修正願います。draw_rec_onとdraw_recandlinesを同時に1にはできません。")
    sys.exit(2)
# 不整合2:extract_1table_on=1 のときはmod_degree=1でも0にする
# 理由：前者で1tableごとに水平を取るため
if extract_1table_on ==1 and mod_degree_on ==1:
    print("configでextract_1table_onのときは、mod_degree込みのためmod_degree=0にします")
    mod_degree_on = 0
# 不整合3:extract_1table_on=0 のときdraw_recandlines_on=1のとき
# 複数テーブルのままの状態で、draw_recandlinesは使えない。
# しかし、たまたまページには1つのテーブルの場合、draw_recandlinesしたいときがある。
# よってワーニングのみ
if extract_1table_on ==0 and draw_recandlines_on ==1:
    print("configのdraw_recandlines=1は、表が1つの時のみ使えます。extract_1table_on=0のため元のページに1表のみ成功します。")


if ( (convdpi < 100) or (convdpi > 400) ):
    print('解像度は100以上400以下にしましょう。pdf2img.iniファイルを修正してください。')
    sys.exit()
if ( (convquality < 0) or (convquality > 100) ):
    print('JPEG qualityは0以上100以下にしましょう。pdf2img.iniファイルを修正してください。')
    sys.exit()

# ディレクトリ配下のpdfファイル一覧を表示
# for pdf_file in glob.glob(in_dir + "/**/*.pdf", recursive=True):
# ディレクトリ配下のpdf、jpg、jpegファイル対応実施。
pdfjpg_files = []
imgs = []
for root, dirs, files in os.walk(in_dir):
    for file in files:
        if file.endswith((".jpg", ".jpeg", ".pdf")): # The arg can be a tuple of suffixes to look for
            print(os.path.join(root, file))
            pdfjpg_files.append(os.path.join(root, file))

# pdffileごとのループ(実はjpg,jpegファイルの場合でも対応している)
for pdf_file in pdfjpg_files:
    print(pdf_file)
    root,ext = os.path.splitext(pdf_file) # extはjpg,pdfチェックに使う
    base_without_ext = os.path.splitext(os.path.basename(pdf_file))[0]
    out_dir2 = out_dir1 + '/' + base_without_ext
    if os.path.exists(out_dir2):
        print("既に出力フォルダがあります。出力ファイル名が重なるときは現在日時をファイル名に追記します。")
    os.makedirs(out_dir2, exist_ok=True)
    # os.makedirs(out_dir2)

    # imgs = pdf2image.convert_from_path(pdf_file, grayscale=True, dpi=convdpi)
    if ext == '.pdf':
        imgs = pdf2image.convert_from_path(pdf_file, dpi=convdpi)
    else: # jpegまたはjpegファイル
        imgs.clear()
        im = Image.open(pdf_file)
        imgs.append(im)

    for index, img in enumerate(imgs):
        cvimage = np.asarray(img)
        # cvimage = cv2.cvtColor(cvimage, cv2.COLOR_RGB2BGR)
        # gryimage = cv2.cvtColor(cvimage, cv2.COLOR_BGR2GRAY)

        PILimage = Image.fromarray(cvimage)

        # 関数fm_extract_1tableをコール
        if ( extract_1table_on == 1 ):
            print("【表分割】1つの表はマウス左ボタンで左上,右下,水平用2点の合計4点クリックです。")
            print("【表分割】それを表の数だけ繰り返してください。")
            print("【表分割】クリック取消は右ボタン、終了は、マウス中ボタンかEnterキーです。")
            print("【表分割】表分割しないときは、最初にマウス中ボタンかEnterキーで次のステップにスキップします。")
            extract_PILimages = fm_extract_1table(PILimage)

        else:
        # 複数イメージ分割もそうでないものもこの配列に入れて以下を共通化。但しpdf/jpg fileループで初期化すること。
            extract_PILimages.clear()
            extract_PILimages.append(PILimage)

        # 関数fm_mod_degreeをコール
        if ( mod_degree_on == 1 ):
            for extract_image in extract_PILimages:
                # PILimage = fm_mod_degree(PILimage)
                extract_image = fm_mod_degree(extract_image)
        # 関数fm_draw_recをコール
        if ( draw_rec_on == 1 ):
            print("【枠のみ】1つの表の枠を書く場所ににマウス左ボタンで左上,右下の合計2点クリックです。")
            print("【枠のみ】それを表の数だけ繰り返してください。")
            print("【枠のみ】クリック取消は右ボタン、終了は、マウス中ボタンかEnterキーです。")
            print("【枠のみ】枠を書かないときは、マウス中ボタンかEnterキーで出力します。")
            for extract_image in extract_PILimages:
                # PILimage, points_array = fm_draw_rec(PILimage, draw_rec_thick, mod_flag)
                tmpimg, points_array = fm_draw_rec(extract_image, draw_rec_thick, mod_flag)

                out_PILimages.append(tmpimg)

        if (draw_recandlines_on == 1):
            print("【枠と縦罫線】表が1つずつ表示されます。枠と縦罫線を書いていきます。")
            print("【枠と縦罫線】枠を書く場所ににマウス左ボタンで左上,右下の2点、縦罫線分Ｘ座標を合わせて左ボタンクリックです。")
            print("【枠と縦罫線】クリック取消は右ボタン、終了は、マウス中ボタンかEnterキーです。")
            print("【枠と縦罫線】表の数だけイメージが表示されるので上記を繰り返します。")
            print("【枠と縦罫線】書かないときは、マウス中ボタンかEnterキーで出力します。")
            for extract_image in extract_PILimages:
                # PILimage, points_array = fm_draw_rec(PILimage, draw_rec_thick, mod_flag)
                tmpimg, points_array = fm_draw_recandlines(
                    extract_image, draw_rec_thick, draw_line_thick, mod_flag)

                out_PILimages.append(tmpimg)
    # for index end

    logger.info(points_array)

    ii = 0
    for tmpimg in out_PILimages:
        dt_now = datetime.datetime.now()
        t03 = dt_now.strftime('%Y%m%d%H%M%S')
        iii = index+1
        t01 = out_dir2 + '/' + base_without_ext # 拡張子前まで
        t02 = "-{0:05}-{1:02}".format(iii,ii)
        t11 = ".jpg"
        tmpimgfile = t01 + t02 + t11
        print(tmpimgfile)
        if os.path.exists(tmpimgfile):
            print("出力イメージファイル名が重複したので、日時付けて別名で保存します。")
            tmpimgfile = t01 + t02 + '-' + t03 + t11

        tmpimg.save(tmpimgfile, dpi=(convdpi, convdpi), quality=convquality)

        """
        tmpimg.save( (out_dir2 + '/' + base_without_ext + \
            '-{:05}-{:02}.jpg'.format(index + 1,ii)),
            dpi=(convdpi,convdpi) , quality=convquality)
        """
        # cv2.imwrite( (out_dir2 + '/' + base_without_ext + \
        #              '-{:05}.jpg'.format(index + 1)), gryimage ,
        #             [cv2.IMWRITE_JPEG_QUALITY, convquality])
        ii += 1
        # for tmpimg 終わり

    # 複数イメージ分割もそうでないものもこの配列に入れて以下を共通化。但しpdf/jpg fileループで初期化すること。
    extract_PILimages.clear()
    out_PILimages.clear()
    # for pdf,jpeg file loop 終わり