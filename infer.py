import argparse
import os
import glob

import torch
import torch.nn.functional as F
import torchaudio
from torchaudio.functional import resample

from tqdm import tqdm

from module.convertor import Convertor

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--inputs', default="./inputs/")
parser.add_argument('-o', '--outputs', default="./outputs/")
parser.add_argument('-m', '--models', default='./models/')
parser.add_argument('-p', '--pitch-shift', default=0, type=float)
parser.add_argument('-t', '--target', default='./target.wav')
parser.add_argument('-d', '--device', default='cpu')
parser.add_argument('-a', '--alpha', default=0, type=float)
parser.add_argument('-idx', '--index', default='NONE')
parser.add_argument('--normalize', default=False, type=bool)
parser.add_argument('-c', '--chunk', default=0, type=int)
parser.add_argument('-adain', default=False, type=bool)
parser.add_argument('-pe', '--pitch-estimation', default='default', choices=['default', 'dio', 'harvest'])

args = parser.parse_args()

device = torch.device(args.device)

convertor = Convertor()
convertor.load(args.models)
convertor.to(device)

if not os.path.exists(args.outputs):
    os.mkdir(args.outputs)


if args.index == 'NONE':
    print("Loading target...")
    wf, sr = torchaudio.load(args.target)
    wf = wf.to(device)
    wf = resample(wf, sr, 16000)
    wf = wf[:1]
    print("Encoding...")
    tgt = convertor.encode_target(wf)
else:
    print("Loading index...")
    tgt = torch.load(args.index).to(device)


paths = glob.glob(os.path.join(args.inputs, "*"))
for i, path in enumerate(paths):
    wf, sr = torchaudio.load(path)
    wf = resample(wf, sr, 16000)
    wf = wf.mean(dim=0, keepdim=True)
    print(f"converting {path}")
    if args.chunk == 0:
        wf = convertor.convert(wf.to(device), tgt, args.pitch_shift, alpha=args.alpha)
    else:
        total_length = wf.shape[1]
        
        wf = torch.cat([wf, torch.zeros(1, (args.chunk * 3))], dim=1)

        wf = wf.unsqueeze(1).unsqueeze(1)
        wf = F.pad(wf, (args.chunk, args.chunk, 0, 0))
        chunks = F.unfold(wf, (1, args.chunk * 3), stride=args.chunk)
        chunks = chunks.transpose(1, 2).split(1, dim=1)

        result = []
        with torch.inference_mode():
            for chunk in tqdm(chunks):
                chunk = chunk.squeeze(1)

                chunk = convertor.convert(chunk.to(device),
                                          tgt,
                                          args.pitch_shift,
                                          alpha=args.alpha,
                                          adain=args.adain,
                                          pitch_estimation_algorithm=args.pitch_estimation)

                chunk = chunk[:, args.chunk:-args.chunk]
                result.append(chunk.to('cpu'))
            wf = torch.cat(result, dim=1)[:, :total_length]
    wf = resample(wf, 16000, sr)
    wf = wf.cpu().detach()
    # normalize
    if args.normalize:
        wf = wf / (wf.abs().max() + 1e-8)
    file_name = f"{os.path.splitext(os.path.basename(path))[0]}"
    torchaudio.save(os.path.join(args.outputs, f"{file_name}.wav"), src=wf, sample_rate=sr)
