# FasterSVC : 蒸留モデルとk近傍法に基づく高速な声質変換
(このリポジトリは実験段階のものです。内容は予告なく変更される場合があります。)

## モデル構造
![Architecture](../images/fastersvc_architecture.png)
デコーダーの構造はFastSVCやStreamVC, Hifi-GAN等を参考に設計。
未来の情報を参照しない"Causal"な畳み込み層を使用することで低遅延を実現。

## 特徴
- リアルタイム変換
- 低遅延 (約0.2秒程度、環境や最適化によって変化する可能性あり。)
- 位相とピッチが安定している (ソースフィルタモデルに基づく。)
- k近傍法による話者スタイル変換

## 必要なもの
- Python 3.10 以降
- PyTorch 2.0以降と GPU 環境
- フルスクラッチで訓練する場合は多数の人間の音声データを用意すること。(LJ SpeechやJVS コーパスなど。)

## インストール
1. このリポジトリをクローン
```sh
git clone https://github.com/uthree/fastersvc.git
```
2. 依存関係をインストール
```sh
pip3 install -r requirements.txt
```
## 事前学習モデルをダウンロードする
JVSコーパスで事前学習したモデルを[こちら](https://huggingface.co/uthree/fastersvc-jvs-corpus-pretrained)にて公開しています。

## 事前学習
基礎的な音声変換を行うモデルを学習する。この段階では特定の話者に特化したモデルになるわけではないが、基本的な音声合成ができるモデルをあらかじめ用意しておくことで、少しの調整だけで特定の話者に特化したモデルを学習することができる。

以下に手順を示す。
1. ピッチ推定器を学習  
WORLDのharvestアルゴリズムによるピッチ推定を高速かつ並列に処理可能な1次元CNNで蒸留する。
```sh
python3 train_pe.py <dataset path>
```

2. コンテンツエンコーダーを学習。  
HuBERT-baseを蒸留する。WavLMの論文によると、第4, 9層に話者と音素情報が含まれているので、それを蒸留する。(第4層の特徴量から線形変換で話者分類ができる。)
```sh
python3 train_ce.py <dataset path>
```

3. デコーダーを学習  
デコーダーは、ピッチとコンテンツから元の波形を再構築することを目標とする。

```sh
python3 train_dec.py <datset.path>
```

## ファインチューニング
事前学習したモデルを、特定話者への変換に特化したモデルに調整することによって、より精度の高いモデルを製作することが可能です。この工程は事前学習と比べて非常に少ない時間で完了します。
1. 特定話者の音声ファイルのみを一つのフォルダにまとめる。
2. デコーダーをファインチューニングする。
```sh
python3 train_dec.py <特定話者の音声ファイルだけがあるフォルダ>
```
3. ベクトル検索用の辞書を作成する。これにより毎回音声ファイルをエンコードする必要がなくなります。
```sh
python3 extract_index.py <特定話者の音声ファイルだけがあるフォルダ> -o <辞書の出力先(任意)>
```
4. 推論する際は`-idx <辞書ファイル>`オプションをつけることで任意の辞書データを読み込むことができます。

### 学習オプション
- `-fp16 True` をつけると16ビット浮動小数点数による学習が可能。RTXシリーズのGPUの場合のみ可能。
- `-b <number>` でバッチサイズを変更。デフォルトは `16`。
- `-e <number>` でエポック数を変更。 デフォルトは `60`。
- `-d <device name>` で演算デバイスを変更。 デフォルトは`cuda`。

## 推論
1. `inputs` フォルダを作成する。
2. `inputs` フォルダに変換したい音声ファイルを入れる
3. 推論スクリプトを実行する
```sh
python3 infer.py -t <ターゲットの音声ファイル>
```

### 追加のオプション
- `-a <0.0から1.0の数値>`で元音声情報の透過率を設定できます。
- `--normalize True` で、音量を正規化できます。
- `-d <デバイス名>` で演算デバイスを変更できます。もともと高速なのであまり意味がないかもしれませんが。
- `-p <音階>` でピッチシフトを行うことができます。男女間の音声変換に有用です。

## pyaudioによるリアルタイム推論 (テスト段階の機能です)
1. オーディオデバイスのIDを確認
```sh
python3 audio_device_list.py
```

2. 実行
```sh
python3 infer_streaming.py -i <入力デバイスID> -o <出力デバイスID> -l <ループバックデバイスID> -t <ターゲットの音声ファイル>
```
(ループバックのオプションはつけなくても動作します。)

## 参考文献
- [FastSVC](https://arxiv.org/abs/2011.05731)
- [kNN-VC](https://arxiv.org/abs/2305.18975)
- [WavLM](https://arxiv.org/pdf/2110.13900.pdf) (Fig. 2)
- [StreamVC](https://arxiv.org/abs/2401.03078v1)
- [Hifi-GAN](https://arxiv.org/abs/2010.05646)
- [AdaIN](https://arxiv.org/abs/1703.06868)
