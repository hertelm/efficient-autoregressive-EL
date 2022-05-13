FROM pytorch/pytorch:1.7.0-cuda11.0-cudnn8-runtime

RUN pip install pytorch-lightning==1.3
RUN pip install transformers==4.0
RUN pip install torchmetrics==0.7.2
RUN pip install jsonlines

COPY . .