#
# Experiment Entry point
# 1. Trains model on Syn Data
# 2. Generates CelebA Data
# 3. Trains on Syn + CelebA Data
#

import torch
import torchvision
from torchvision import transforms
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import torch.nn as nn
import argparse

import wandb
from data_loading import *
from utils import *
from shading import *
from train import *
from models import *

def main():
    ON_SERVER = True

    parser = argparse.ArgumentParser(description='SfSNet - Residual')
    parser.add_argument('--batch_size', type=int, default=8, metavar='N',
                        help='input batch size for training (default: 8)')
    parser.add_argument('--epochs', type=int, default=10, metavar='N',
                        help='number of epochs to train (default: 10)')
    parser.add_argument('--lr', type=float, default=0.001, metavar='LR',
                        help='learning rate (default: 0.001)')
    parser.add_argument('--wt_decay', type=float, default=0.0005, metavar='W',
                        help='SGD momentum (default: 0.0005)')
    parser.add_argument('--no_cuda', action='store_true', default=False,
                        help='disables CUDA training')
    parser.add_argument('--seed', type=int, default=1, metavar='S',
                        help='random seed (default: 1)')
    parser.add_argument('--read_first', type=int, default=-1,
                        help='read first n rows (default: -1)')
    parser.add_argument('--details', type=str, default=None,
                        help='Explaination of the run')
    if ON_SERVER:
        parser.add_argument('--syn_data', type=str, default='/nfs/bigdisk/bsonawane/sfsnet_data/',
                        help='Synthetic Dataset path')
        parser.add_argument('--celeba_data', type=str, default='/nfs/bigdisk/bsonawane/CelebA-dataset/celeba_sfsnet_gen_20k/',
                        help='CelebA Dataset path')
        parser.add_argument('--log_dir', type=str, default='./results/',
                        help='Log Path')
    else:  
        parser.add_argument('--syn_data', type=str, default='../data/sfs-net/',
                        help='Synthetic Dataset path')
        parser.add_argument('--celeba_data', type=str, default='../data/celeba/',
                        help='CelebA Dataset path')
        parser.add_argument('--log_dir', type=str, default='./results/',
                        help='Log Path')
    parser.add_argument('--load_model', type=str, default=None,
                        help='load model from')
    args = parser.parse_args()
    use_cuda = not args.no_cuda and torch.cuda.is_available()

    torch.manual_seed(args.seed)

    # initialization
    syn_data = args.syn_data
    celeba_data = args.celeba_data
    batch_size = args.batch_size
    lr         = args.lr
    wt_decay   = args.wt_decay
    log_dir    = args.log_dir
    epochs     = args.epochs
    model_dir  = args.load_model
    read_first = args.read_first

    
    if read_first == -1:
        read_first = None

    # Debugging and check working
    # syn_train_csv = syn_data + '/train.csv'
    # train_dataset, _ = get_sfsnet_dataset(syn_dir=syn_data+'train/', read_from_csv=syn_train_csv, read_celeba_csv=None, read_first=read_first, validation_split=5)
    # train_dl  = DataLoader(train_dataset, batch_size=10, shuffle=False)
    # validate_shading_method(train_dl)
    # return 

    # Init WandB for logging
    wandb.init(project='SfSNet-CelebA-Shader-Correcting-Net')
    wandb.log({'lr':lr, 'weight decay': wt_decay})

    # Initialize models
    conv_model            = baseFeaturesExtractions()
    normal_residual_model = NormalResidualBlock()
    albedo_residual_model = AlbedoResidualBlock()
    light_estimator_model = LightEstimator()
    normal_gen_model      = NormalGenerationNet()
    albedo_gen_model      = AlbedoGenerationNet()
    shading_model         = sfsNetShading()
    image_recon_model     = ReconstructImage()
    neural_light_model    = NeuralLatentLightEstimator()
    shading_correctness_model = ShadingCorrectNess()
    
    sfs_net_model      = SfsNetPipeline(conv_model, normal_residual_model, albedo_residual_model, \
                                            light_estimator_model, normal_gen_model, albedo_gen_model, \
                                            shading_model, neural_light_model, shading_correctness_model, image_recon_model)
 
    if use_cuda:
        sfs_net_model = sfs_net_model.cuda()

    if model_dir is not None:
        sfs_net_model.load_state_dict(torch.load(model_dir + 'sfs_net_model.pkl'))
    else:
        print('Initializing weights')
        sfs_net_model.apply(weights_init)

    os.system('mkdir -p {}'.format(args.log_dir))
    with open(args.log_dir+'/details.txt', 'w') as f:
        f.write(args.details)

    wandb.watch(sfs_net_model)
           
    # 1. Train on both Synthetic and Real (Celeba) dataset
    train(sfs_net_model, syn_data, celeba_data=celeba_data, read_first=read_first,\
            batch_size=batch_size, num_epochs=epochs, log_path=log_dir+'Mix_Training/', use_cuda=use_cuda, wandb=wandb, \
            lr=lr, wt_decay=wt_decay)
    
if __name__ == '__main__':
    main()
