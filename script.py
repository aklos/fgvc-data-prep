import os
import subprocess
import shutil
from PIL import Image

def run_cmd(cmd, silent=True):
    out = subprocess.getoutput(cmd)
    if not silent:
        print(out)

def decompose():
    print('decomposing video and mask')

    run_cmd('rm -r ./temp')
    run_cmd('mkdir -p ./temp')

    if os.path.isfile('input/video.mp4'):
        run_cmd('mkdir -p ./temp/v_decomp')
        run_cmd('ffmpeg -i ./input/video.mp4 ./temp/v_decomp/%05d.png -hide_banner')
        run_cmd('cd ./temp/v_decomp && ls -v | cat -n | while read n f; do mv -n "$f" "$n.png"; done')
        run_cmd('''cd ./temp/v_decomp && rename -e 's/\d+/sprintf("%05d",$& - 1)/e' -- *.png''')

    if os.path.isfile('input/mask.mp4'):
        run_cmd('mkdir -p ./temp/m_decomp')
        run_cmd('ffmpeg -i ./input/mask.mp4 ./temp/m_decomp/%05d.png -hide_banner')
        run_cmd('cd ./temp/m_decomp && ls -v | cat -n | while read n f; do mv -n "$f" "$n.png"; done')
        run_cmd('''cd ./temp/m_decomp && rename -e 's/\d+/sprintf("%05d",$& - 1)/e' -- *.png''')
    elif os.path.isfile('input/mask.png'):
        file_count = len([f for f in os.listdir('./temp/v_decomp') if os.path.isfile(os.path.join('./temp/v_decomp', f))])
        run_cmd('mkdir -p ./temp/m_decomp')
        run_cmd('cp ./input/mask.png ./temp/m_decomp')
        for i in range(0, file_count):
            run_cmd('cp ./temp/m_decomp/mask.png ./temp/m_decomp/%05d.png' % i)
        run_cmd('rm ./temp/m_decomp/mask.png')

def resize(width, height):
    print('resizing images')

    def resize_in_folder(folder):
        images = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

        for i in images:
            image = Image.open(os.path.join(folder, i))
            new_image = image.resize((width, height))
            new_image.save(os.path.join(folder, i))

    resize_in_folder('./temp/v_decomp')
    resize_in_folder('./temp/m_decomp')

def split(num):
    print('splitting into parts')

    run_cmd('rm -r ./output')
    run_cmd('mkdir -p ./output')

    def split_folder(folder, affix):
        images = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

        subfolder = 1
        for i, image in enumerate(images):
            if i != 0 and i % num == 0:
                subfolder += 1

            run_cmd('mkdir -p ./output/%d%s' % (subfolder, affix))
            shutil.move(os.path.join(folder, image), os.path.join('./output/%d%s' % (subfolder, affix), image))

            if i % num == num - 1:
                run_cmd('cd ./output/%d%s && ls -v | cat -n | while read n f; do mv -n "$f" "$n.png"; done' % (subfolder, affix))
                run_cmd(('cd ./output/%d%s && ' % (subfolder, affix)) + '''rename -e 's/\d+/sprintf("%05d",$& - 1)/e' -- *.png''')

    split_folder('./temp/v_decomp', 'v')
    split_folder('./temp/m_decomp', 'm')

    run_cmd('rm -r ./temp')

if __name__ == '__main__':
    decompose()
    resize(480, 256)
    split(10)

