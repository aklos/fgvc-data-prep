import os
import io
import subprocess
import shutil
import sys, getopt
from PIL import Image
from PIL import ImageCms

def run_cmd(cmd, silent=True):
    out = subprocess.getoutput(cmd)
    if not silent:
        print(out)

def fix_color_profile():
    print('fixing mask color profile')

    def convert_to_srgb(img):
        '''Convert PIL image to sRGB color space (if possible)'''
        icc = img.info.get('icc_profile', '')
        if icc:
            io_handle = io.BytesIO(icc)     # virtual file
            src_profile = ImageCms.ImageCmsProfile(io_handle)
            dst_profile = ImageCms.createProfile('sRGB')
            img = ImageCms.profileToProfile(img, src_profile, dst_profile)
        return img

    if os.path.isfile('input/mask.png'):
        img = Image.open('input/mask.png')
        img_conv = convert_to_srgb(img)
        if img.info.get('icc_profile', '') != img_conv.info.get('icc_profile', ''):
            # ICC profile was changed -> save converted file
            img_conv.save('input/mask.png', icc_profile = img_conv.info.get('icc_profile',''))

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

def split(num, keep_num = None):
    print('splitting into parts')
    if keep_num:
        print('keeping part %d' % keep_num)

    run_cmd('rm -r ./output')
    run_cmd('mkdir -p ./output')

    def split_folder(folder, affix):
        images = sorted([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])

        subfolder = 1
        for i, image in enumerate(images):
            if i != 0 and i % num == 0:
                subfolder += 1

            if keep_num and subfolder != keep_num:
                continue

            run_cmd('mkdir -p ./output/%d%s' % (subfolder, affix))
            shutil.move(os.path.join(folder, image), os.path.join('./output/%d%s' % (subfolder, affix), image))

            # Rename all images if this is the last one in the split, or the final image
            if i % num == num - 1 or i == len(images) - 1:
                run_cmd('cd ./output/%d%s && ls -v | cat -n | while read n f; do mv -n "$f" "$n.png"; done' % (subfolder, affix))
                run_cmd(('cd ./output/%d%s && ' % (subfolder, affix)) + '''rename -e 's/\d+/sprintf("%05d",$& - 1)/e' -- *.png''')

    split_folder('./temp/v_decomp', 'v')
    split_folder('./temp/m_decomp', 'm')

    run_cmd('rm -r ./temp')

if __name__ == '__main__':
    _, args = getopt.getopt(sys.argv, ['fix', 'decompose', 'resize=', 'split=', 'keep='])
    if '--fix' in args:
        fix_color_profile()
    if '--decompose' in args:
        decompose()
    resize_arg = next(iter([x for x in args if x.startswith('--resize')]), None)
    if resize_arg:
        dims = [int(x) for x in resize_arg.split('=')[1].split('x')]
        resize(dims[0], dims[1])
    split_arg = next(iter([x for x in args if x.startswith('--split')]), None)
    keep_arg = next(iter([x for x in args if x.startswith('--keep')]), None)
    if split_arg:
        num = int(split_arg.split('=')[1])
        keep_num = None
        if keep_arg:
            keep_num = int(keep_arg.split('=')[1])
        split(num, keep_num)

