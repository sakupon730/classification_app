import cv2
from PIL import Image
import os
import numpy as np

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torch.utils.data as data
from torchvision import datasets, transforms
import torchvision.models as models

import pytorch_lightning as pl

from flask import Flask, render_template, request, redirect, abort, flash
from werkzeug.utils import secure_filename


def expand2square(pil_img):
    width, height = pil_img.size
    
    if width == height:
        return pil_img
    
    elif width > height:
        result = Image.new(pil_img.mode, (width, width), color='white')
        result.paste(pil_img, (0, (width - height) // 2))
        return result
    
    else:
        result = Image.new(pil_img.mode, (height, height), color='white')
        result.paste(pil_img, ((height - width) // 2, 0))
        return result

class ResNetModel(pl.LightningModule):
    def __init__(self):
            super(ResNetModel, self).__init__()
            self.resnet = models.resnet18(pretrained=True)
            self.resnet.fc = nn.Linear(in_features=512, out_features=3, bias=True)
            
    def forward(self, x):
        x = self.resnet(x)
        
        return x

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = ResNetModel.load_from_checkpoint(checkpoint_path='test.ckpt', strict=False)
model.eval()
model.to(device)

app = Flask(__name__)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'gif'])
UPLOAD_FOLDER = './static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == "GET":
        return render_template("index.html")

    if request.method == "POST":
        if 'file' not in request.files:
            flash('ファイルがありません')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('ファイルがありません')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # 画像を読み込み
        image = Image.open(filepath)
        if image.size[0] != image.size[1]:
            image = np.array(expand2square(image))
        image = cv2.resize(image, (224, 224)).transpose(2,0,1)
        image = torch.from_numpy(image.astype(np.float32)).clone()
        image = image.unsqueeze(0)
        image = image.to(device)

        # 予測を実施
        out = model(image)
        _, pred = torch.max(out, 1)
        result = pred[0].item()
        classes = ['鳥', '猫', '犬']
        
        return render_template("index.html", filepath=filepath, result=classes[result])


if __name__ == '__main__':
    app.run(debug=True)