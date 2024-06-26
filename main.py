import argparse
import os

import torch
import torch.nn as nn
from scipy.io import wavfile
from torch import optim
from torch.autograd import Variable
from torch.utils.data import DataLoader
from tqdm import tqdm
import data_preprocess
import model1
import numpy as np

from data_preprocess import sample_rate
from model import Generator, Discriminator
from utils import AudioDataset, emphasis
import matplotlib.pyplot as plt



d_clean_loss_list = []
d_noisy_loss_list = []
g_loss_list = []







if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train Audio Enhancement')
    parser.add_argument('--batch_size', default=50, type=int, help='train batch size')
    parser.add_argument('--num_epochs', default=86, type=int, help='train epochs number')

    opt = parser.parse_args()
    BATCH_SIZE = opt.batch_size
    NUM_EPOCHS = opt.num_epochs
    
    
    
    
    # loss fuction to calculate the mdct mdct_rmse
    def stft_rmse_loss(clean_batch, lossy_batch, n_fft=2048, hop_length=512):
      
        
        assert clean_batch.shape == lossy_batch.shape, "Clean and lossy batches must have the same shape"
        
        batch_size, _, signal_length = clean_batch.shape
        total_loss = 0.0
        
        output1 = clean_batch.cpu().detach().numpy()  # Extract clean audio signal
        output2 = lossy_batch.cpu().detach().numpy()  # Extract clean audio signal
        
        # output1 = train_clean1.cpu().detach().numpy()
        shape = output1.shape
        # print(shape[0])
        batch = shape[0]
        
        
        # Compute STFT and RMSE loss for each signal in the batch
        for i in range(batch):
            # lossy_audio = lossy_batch[i, 0, :]  # Extract lossy audio signal
            
            # Compute STFT for clean and lossy signals
            clean_mdct = data_preprocess.mdct(output1[i][0])
            lossy_mdct = data_preprocess.mdct(output2[i][0])
            
            # Compute magnitude spectrograms and RMSE loss
            clean_mag = np.abs(clean_mdct)
            lossy_mag = np.abs(lossy_mdct)
            rmse = np.sqrt(np.mean((clean_mag - lossy_mag)**2))
            
            total_loss += rmse  # Accumulate RMSE loss
        
        mean_loss = total_loss / batch_size  # Compute mean RMSE loss across the batch
        return mean_loss
    
    

    # load data
    print('loading data...')
    train_dataset = AudioDataset(data_type='train')
    test_dataset = AudioDataset(data_type='test')
    train_data_loader = DataLoader(dataset=train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=4)
    test_data_loader = DataLoader(dataset=test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=4)
    # generate reference batch
    ref_batch = train_dataset.reference_batch(BATCH_SIZE)

    # create D and G instances
    discriminator = Discriminator()
    generator = Generator()
    if torch.cuda.is_available():
        discriminator.cuda()
        generator.cuda()
        ref_batch = ref_batch.cuda()
    ref_batch = Variable(ref_batch)
    print("# generator parameters:", sum(param.numel() for param in generator.parameters()))
    print("# discriminator parameters:", sum(param.numel() for param in discriminator.parameters()))
    # optimizers
    g_optimizer = optim.Adam(generator.parameters(), lr=0.001)
    d_optimizer = optim.Adam(discriminator.parameters(), lr=0.001)

    for epoch in range(NUM_EPOCHS):
        train_bar = tqdm(train_data_loader)
        for train_batch, train_clean, train_noisy in train_bar:
            
            # ---------------------cnvrt signals mdct
            
            train_noisy_mdct = data_preprocess.mdctconvert(train_noisy,BATCH_SIZE)
            

            # latent vector - normal distribution
            z = nn.init.normal(torch.Tensor(train_batch.size(0), 1024, 8))
            if torch.cuda.is_available():
                train_batch, train_clean, train_noisy,train_noisy_mdct= train_batch.cuda(), train_clean.cuda(), train_noisy.cuda(),train_noisy_mdct.cuda()
                z = z.cuda()
            train_batch, train_clean, train_noisy,train_noisy_mdct = Variable(train_batch), Variable(train_clean), Variable(train_noisy),Variable(train_noisy_mdct)
            z = Variable(z)

            # TRAIN D to recognize clean audio as clean
            # training batch pass
            discriminator.zero_grad()
            outputs = discriminator(train_batch, ref_batch)
            clean_loss = torch.mean((outputs - 1.0) ** 2)  # L2 loss - we want them all to be 1
            clean_loss.backward()

            # TRAIN D to recognize generated audio as noisy
            # train_noisy_mdct = data_preprocess.mdctconvert(train_noisy,BATCH_SIZE)
            
            # float_tensor = int_tensor.to(torch.float)
            generated_outputs = generator(train_noisy_mdct)
            generated_outputs = generated_outputs*2
            # generated out*noisy ---------------- to be done
            # gen_mdct = data_preprocess.mdct(generated_outputs)
            maskapplied = train_noisy*generated_outputs
            # print("abcd    ",maskapplied.shape)
            # print("abcd    ",train_noisy_mdct.shape)
            outputs = discriminator(torch.cat((maskapplied, train_noisy), dim=1), ref_batch)
            noisy_loss = torch.mean(outputs ** 2)  # L2 loss - we want them all to be 0
            noisy_loss.backward()

            d_loss = clean_loss + noisy_loss
            # d_loss.backward()
            d_optimizer.step()  # update parameters

            # TRAIN G so that D recognizes G(z) as real
            generator.zero_grad()
            output1 = train_noisy.cpu().detach().numpy()
            generated_outputs = generator(train_noisy_mdct)
            generated_outputs = generated_outputs*2
            maskapplied = train_noisy*generated_outputs
            # gen_mdct = data_preprocess.mdct(generated_outputs)
            gen_noise_pair = torch.cat((maskapplied, train_noisy), dim=1)
            outputs = discriminator(gen_noise_pair, ref_batch)
            # output1 = outputs.cpu().detach().numpy()
            # gen_mdct = data_preprocess.mdct(output1)
            # print(outputs)

            g_loss_ = 0.5 * torch.mean((outputs - 1.0) ** 2)
            # L1 loss between generated output and clean sample
            
            
            
            
            mdct_rmse = stft_rmse_loss(maskapplied, train_clean)

            # Now mdct_rmse is already a float value representing the loss
            # No need to convert it back to a torch tensor
            # g_loss = torch.tensor(mdct_rmse, dtype=torch.float64, requires_grad=True)
            # g_loss_ = torch.tensor(1.0, dtype=torch.float64, requires_grad=True)

            
            # mdct_rmse = stft_rmse_loss(generated_outputs,train_clean)
            l1_dist = torch.abs(torch.add(maskapplied, torch.neg(train_clean)))
            g_cond_loss = 100 * torch.mean(l1_dist)  # conditional loss
            g_loss = g_loss_ + g_cond_loss
            # mdct_rmse = torch.from_numpy(np.array(mdct_rmse)).to(torch.float64)
            
            # g_loss = mdct_rmse
            # g_loss_ = torch.tensor(1.0, requires_grad=False)

            # backprop + optimize
            



            g_loss.backward()
            g_optimizer.step()

            train_bar.set_description(
                'Epoch {}: d_clean_loss {:.4f}, d_noisy_loss {:.4f}, g_loss {:.4f}, g_conditional_loss '
                    .format(epoch + 1, clean_loss, noisy_loss, g_loss))
            
            # d_clean_loss_list.append(clean_loss.cpu().detach().numpy())
            # d_noisy_loss_list.append(noisy_loss.cpu().detach().numpy())
            # g_loss_list.append(g_loss.cpu().detach().numpy())

            
            
            
        g_path_prev = os.path.join('epochs', 'generator-{}.pkl'.format(epoch - 1))
        d_path_prev = os.path.join('epochs', 'discriminator-{}.pkl'.format(epoch - 1))
        if os.path.exists(g_path_prev):
            os.remove(g_path_prev)
            os.remove(d_path_prev)

            print(f"Removed {g_path_prev} and {d_path_prev}")

        g_path = os.path.join('epochs', 'generator-{}.pkl'.format(epoch + 1))
        d_path = os.path.join('epochs', 'discriminator-{}.pkl'.format(epoch + 1))
        torch.save(generator.state_dict(), g_path)
        torch.save(discriminator.state_dict(), d_path)

        # TEST model
        test_bar = tqdm(test_data_loader, desc='Test model and save generated audios')
        for test_file_names, test_noisy in test_bar:
            z = nn.init.normal(torch.Tensor(test_noisy.size(0), 1024, 8))
            if torch.cuda.is_available():
                test_noisy, z = test_noisy.cuda(), z.cuda()
            test_noisy, z = Variable(test_noisy), Variable(z)
            test_noisy1 = data_preprocess.mdctconvert(test_noisy,32)
            test_noisy1 = test_noisy1.cuda() #changed here from cuda to cpu
            test_noisy1 = Variable(test_noisy1)
            fake_speech = generator(test_noisy1).data.cpu().numpy()  # convert to numpy array
            fake_speech = emphasis(fake_speech, emph_coeff=0.95, pre=False)

            for idx in range(fake_speech.shape[0]):
                generated_sample = fake_speech[idx]
                result_path = os.path.join('results','{}_e{}.wav'.format(test_file_names[idx].replace('.npy', ''), epoch - 1))
                if os.path.exists(result_path):
                    os.remove(result_path)
                    print(f"Removed {result_path}")

                file_name = os.path.join('results',
                                         '{}_e{}.wav'.format(test_file_names[idx].replace('.npy', ''), epoch + 1))
                wavfile.write(file_name, sample_rate, generated_sample.T)

        # save the model parameters for each epoch
       