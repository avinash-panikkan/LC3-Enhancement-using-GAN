import os
import shutil
import librosa

def stereo_to_mono(input_file, output_file):
    # Load the stereo audio file
    y, sr = librosa.load(input_file, mono=False)
    
    # Convert stereo to mono
    mono_y = librosa.to_mono(y)
    
    # Save the mono audio to a new file
    librosa.output.write_wav(output_file, mono_y, sr)

def process_files(source_dir, dest_dir):
    # Create the destination directory if it doesn't exist
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    # Traverse through the source directory
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".wav"):  # Process only WAV files
                input_file = os.path.join(root, file)
                output_file = os.path.join(dest_dir, file)
                
                # Check if the file is stereo
                y, sr = librosa.load(input_file, mono=False)
                if len(y.shape) > 1 and y.shape[0] == 2:
                    # Convert stereo to mono
                    stereo_to_mono(input_file, output_file)
                else:
                    # If already mono, copy the file as is
                    shutil.copy(input_file, output_file)

# Source directory containing the WAV files
print("abc")
source_dir = "D:\Main Project\Project\encode\\testset_lc3"
# Destination directory to store mono files
dest_dir = "D:\Main Project\Project\LC3-Enhancement-using-GAN\data\mono"

# Process files
process_files(source_dir, dest_dir)
