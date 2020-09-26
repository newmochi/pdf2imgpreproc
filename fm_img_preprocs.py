"""
======================================================================
Project Name    : PDFイメージ前処理発掘調査
Program Name    : PDFイメージ矩形取得プログラム
File Name       : fm_img_preprocs.py
Encoding        : utf-8
Creation Date   : 2020.9.13
Append Date     : 2020.9.21 (fm_draw_rectandlines)
Creation User   : Hiroyuki.Mochizuki

Copyright c 2020 Hiroyuki Mochizuki (holiday programmer)

This source code or any portion thereof must not be
reproduced or used in any manner whatsoever.
======================================================================
"""

# 断念 from logging import getLogger, basicConfig, DEBUG
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import warnings;warnings.filterwarnings('ignore')
from PIL import ImageDraw
import copy
import cv2
import math
# log汎用系sub配置 別のファイルでは以下2行
import logging
logger = logging.getLogger(__name__)
# あとは、logger.debug("文字列")
# あとは、logger.info("文字列")
# あとは、logger.warn("文字列")
# あとは、logger.error("文字列")
# あとは、logger.critical("文字列")

def fm_extract_1table(im):
    """
    見開き1ページを2ページにする。その際それぞれ水平補正を行う。
    1ページの指定は、切出しページ左上＋切出しページ右下＋その中の水平線左＋その中の水平線右
    の【4点セット】にて1ページ切出し＋水平補正が行われる。
    1ページのままで良いときは、【4点セット】を1回で良い。リターンはim[0]のみ。
    2ページのときは、【4点セット』を見開き左、見開き右の2階実施。リターンは、im[0],im[1]。
    理論上は、見開き2ページに表が３つあるときに【４点セット】を３回繰り返しても良い。
    Parameters
    ----------
    im: PILイメージ
    ----------
    Returns
    ims: 複数イメージに切出しされてリターン。それぞれ水平補正されている。
    ----------
    """
    im_list=np.asarray(im)  # 何とOpenCVに変換している。
    plt.imshow(im_list)

    a=plt.ginput(n=-1, mouse_add=1, mouse_pop=3, mouse_stop=2)
    # n=-1でインプットが終わるまで座標を取得
    # mouse_addで座標を取得（左クリック）
    # mouse_popでUndo（右クリック）
    # mouse_stopでインプットを終了する（ミドルクリック）
    # 左click1: ページとして切出したい左上座標
    # 左click2: ページとして切出したい右下座標
    # 左click3: 上記座標範囲内にある水平線の左端座標
    # 左click4: 上記座標範囲内にある水平線の右端座標
    # 上記４セットをページに分けたい分繰り返す
    # 中click: 終了

    im_rot = []
    count = 0
    cbak = 0.0
    dbak = 0.0
    int_arg = 0
    count = 0
    page_count = 0
    HORIZONTAL = 0
    for c, d in a:
        count += 1
        print(c, d)
        if count % 4 == 0:
            # 2点指定されたらその座標の角度を測る
            arg = math.degrees(math.atan2((d - dbak), (c - cbak)))
            int_arg = int(arg)
            im_crop = im_crop.rotate(int_arg)
            im_rot.append(im_crop)
            page_count += 1
        elif count % 2 == 0:
            # 2点指定されたらその矩形をイメージとして切出し
            # 引数には４つのパラをかっこでくくること
            # https://note.nkmk.me/python-pillow-image-crop-trimming/:w
            im_crop = im.crop((cbak, dbak, c, d))
        else:
            cbak = c
            dbak = d
        # plt.plot(c, d, "ro")  # グラフ上に座標をマークする

    if count == 0:
        im_rot.append(im)

    return im_rot


def fm_mod_degree(im):
    """
    PILイメージの水平補正を行う。
    ・複数の2点の傾きの平均角度で水平化。
    ・見開きの場合、左ページと右ページの傾きが違っている場合効果薄い。
    ・その場合、見開きのページから「水平補正」＋「矩形切出してファイル化」とする。
    ・それを行うには、関数fm_extract_one_pageを使う。
    Parameters
    ----------
    im: PILイメージ
    ----------
    Returns
    im: 水平補正されたPILイメージ
    ----------
    """

    im_list=np.asarray(im)  # 何とOpenCVに変換している。
    plt.imshow(im_list)

    a=plt.ginput(n=-1, mouse_add=1, mouse_pop=3, mouse_stop=2)
    # n=-1でインプットが終わるまで座標を取得
    # mouse_addで座標を取得（左クリック）
    # mouse_popでUndo（右クリック）
    # mouse_stopでインプットを終了する（ミドルクリック）

    count = 0
    cbak = 0.0
    dbak = 0.0
    sum_arg = 0
    count = 0
    HORIZONTAL = 0
    for c, d in a:
        count += 1
        print(c, d)
        if count % 2 == 0:
            # 2点指定されたらその座標の角度を測る
            arg = math.degrees(math.atan2((d - dbak), (c - cbak)))
            sum_arg += arg
            count += 1
        else:
            cbak = c
            dbak = d
        # plt.plot(c, d, "ro")  # グラフ上に座標をマークする

    if count == 0:
        im = Image.fromarray(im_list)  # cv2からPILにまた戻す(本当はこれも不要)
    else:
        avg_degree = sum_arg / count - HORIZONTAL
        # 以下のopenCVは90度単位なので使えない。よってPillow利用。
        # rotate_im_list = cv2.rotate(im_list, int_avg_degree) # opencv
        # Pillow
        im = im.rotate(avg_degree)
        # im = Image.fromarray(rotate_im_list)  # cv2からPILに戻す必要はなくなった

    return im


def fm_draw_rec(im, i_thick, mod_flag):
    """
    PILイメージに直接矩形(表の視覚的境界)を描画。
    ・2点を指定するたびに矩形の左上と右下を指定。2*N回指定でNこの矩形描画。
    ・fm_mod_degreeを最初にコールして水平補正をすることも可能。
    ・その場合、マウスクリックは引き続き行う。(画面クローズしないので以下)
    [マウス左4回で水平線2階選択、マウス中で終わり、しかし画面上プラスの点が丸に変わるだけ
    で閉じない。引き続きマウス左2回を矩形谷に繰り返し、最後マウス中。ここでやっと画面消える。
    ・その場合の効果が薄いときの対処は、fm_mod_degreeのコメント参照。
    Parameters
    ----------
     im: PILイメージ
     i_thick: 矩形の黒線の太さ(単位dot)
     mod_flag: 矩形の
    ----------
    Returns
    im: 矩形描画されたPILイメージ
    a:  矩形選択した全ての点座標(浮動小数点)
    ----------
    """

    im_list=np.asarray(im)  # 何とOpenCVに変換している。
    plt.imshow(im_list)
    # ポイントの配列を返すだけでイメージ変更しない場合(本当は矩形を書かなければいいがサンプルで日和った処理
    imorg = copy.copy(im) #mod_flag ==0 と無編集の場合のため。冗長ではあるが安全策。

    # thickness=1ならPILのまましかも小数点付き座標で書ける。しかし人のポイント精度から不要と判断。
    # draw = ImageDraw.Draw(im)
    a=plt.ginput(n=-1, mouse_add=1, mouse_pop=3, mouse_stop=2)
    # n=-1でインプットが終わるまで座標を取得
    # mouse_addで座標を取得（左クリック）
    # mouse_popでUndo（右クリック）
    # mouse_stopでインプットを終了する（ミドルクリック）

    count = 0
    cbak = 0.0
    dbak = 0.0
    for c, d in a:
        count += 1
        print(c, d)
        if count % 2 == 0:
            # 左上、右下を指定されたので矩形描画
            # thickness=1ならPILのまましかも小数点付き座標で書ける。しかし人のポイント精度から不要と判断。
            # draw.rectangle( (cbak, dbak, c,d), outline=(0, 0, 0))
            icbak = int(cbak)
            idbak = int(dbak)
            ic = int(c)
            id = int(d)
            cv2.rectangle(im_list, (icbak, idbak), (ic, id), (0, 0, 0), thickness=i_thick, lineType=cv2.LINE_8)
        else:
            cbak = c
            dbak = d
        # plt.plot(c, d, "ro")  # グラフ上に座標をマークする

    # plt.savefig('fig_test.jpg', bbox_inches="tight", pad_inches=0.2)
    # im.save( 'test.jpg', dpi=(400, 400), quality=90)

    im = Image.fromarray(im_list)  # cv2からPILにまた戻す

    if mod_flag == 0:
        a = 0
        return imorg, a  # もし編集したイメージを返さず、配列だけ返す場合
    if count == 0:
        a = 0
        return imorg, a  # もし編集してない場合も、元の画像を返す
    return im, a




def fm_draw_recandlines(im, i_thick, iline_thick, mod_flag):
    """
    PILイメージに直接矩形(表の視覚的境界)を描画。
    【注意】draw_rect関数と違い矩形は1つのみ。(マウス左ボタンまとめてクリックの弊害)
    将来的には、１つの矩形だけでなくforループにして、print関数でまだあるか聞くという手
    しかし、縦冷戦を引くときは、必ず表1つ1つ分解かつ水平を取らないと意味ないので
    インデントな要求がない限りやらない。
    これはポリシー＆1枚ページに複数矩形描画を最小限オペレーションとしたいためでもある。

    1. 最初の左ボタンによる2点は、矩形描画の左上と右下
    2. その際、line用upper_y、lower_y座標をキープ
    3. 次に中ボタンを押すまでの左ボタンは全部縦罫線用X座標

    ・fm_extract_1table(im)をコールしたときのみ、この関数を使える。
    ・fm_mod_degreeは上記extractでやっているので無効に(メインルーチンで)
    Parameters
    ----------
     im: PILイメージ
     i_thick: 矩形の黒線の太さ(単位dot)
     iline_thick: 矩形のY座標を使った黒線の太さ(単位dot)
     mod_flag: 矩形の直接修正をするかのフラグ
    ----------
    Returns
    im: 矩形描画されたPILイメージ
    a:  選択した全ての点座標(浮動小数点)
    ----------
    """

    im_list=np.asarray(im)  # 何とOpenCVに変換している。
    plt.imshow(im_list)
    # ポイントの配列を返すだけでイメージ変更しない場合(本当は矩形を書かなければいいがサンプルで日和った処理
    imorg = copy.copy(im) #mod_flag ==0 と無編集の場合のため。冗長ではあるが安全策。

    a=plt.ginput(n=-1, mouse_add=1, mouse_pop=3, mouse_stop=2)
    # n=-1でインプットが終わるまで座標を取得
    # mouse_addで座標を取得（左クリック）
    # mouse_popでUndo（右クリック）
    # mouse_stopでインプットを終了する（ミドルクリック）

    count = 0
    cbak = 0.0
    dbak = 0.0
    for c, d in a:
        count += 1
        # print(c, d)
        logger.info(str(c))
        logger.info(str(d))
        if count == 1:
            upper_y = int(d) # line用上限X座標キープ
            icbak = int(c) # 矩形左上キープ
            idbak = int(d)  # 矩形左上キープ
        elif count == 2: # 矩形描画
            lower_y = int(d) # line用下限X座標キープ
            # 左上、右下を指定されたので矩形描画
            ic = int(c)
            id = int(d)
            cv2.rectangle(im_list, (icbak, idbak), (ic, id), (0, 0, 0),
                        thickness=i_thick, lineType=cv2.LINE_8)
        else:
            # (ic, upper_y)----(ic, lower_y)の線描画
            ic = int(c) # x座標だけ必要
            cv2.line(im_list, (ic, upper_y), (ic, lower_y), (0, 0, 0),
                        thickness=iline_thick, lineType=cv2.LINE_8)

        # plt.plot(c, d, "ro")  # グラフ上に座標をマークする
        # for 終わり

    # plt.savefig('fig_test.jpg', bbox_inches="tight", pad_inches=0.2)
    # im.save( 'test.jpg', dpi=(400, 400), quality=90)

    im = Image.fromarray(im_list)  # cv2からPILにまた戻す

    if mod_flag == 0:
        return imorg, a  # もし編集したイメージを返さず、配列だけ返す場合
    if count == 0:
        return imorg, a  # もし編集してない場合も、元の画像を返す

    return im, a
