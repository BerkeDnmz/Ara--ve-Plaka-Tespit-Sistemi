import torch
import torch.backends.cudnn as cudnn
import numpy as np
import PIL.Image as pil_image

from lib.model.models import ESPCN
from lib.model.utils import convert_ycbcr_to_rgb, preprocess, calc_psnr


def Espcn(image_path):    
    weight_path = "model/weights/espcn_x3.pth"
    scale = 3

    cudnn.benchmark = True
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

    model = ESPCN(scale_factor=scale).to(device)

    state_dict = model.state_dict()
    for n, p in torch.load(weight_path, map_location=lambda storage, loc: storage).items():
        if n in state_dict.keys():
            state_dict[n].copy_(p)
        else:
            raise KeyError(n)

    model.eval()

    image = pil_image.open(image_path).convert('RGB')

    image_width = (image.width // scale) * scale
    image_height = (image.height // scale) * scale

    hr = image.resize((image_width, image_height), resample=pil_image.BICUBIC)
    lr = hr.resize((hr.width // scale, hr.height // scale), resample=pil_image.BICUBIC)
    bicubic = lr.resize((lr.width * scale, lr.height * scale), resample=pil_image.BICUBIC)
    bicubic.save(image_path.replace('.', '_bicubic_x{}.'.format(scale)))

    lr, _ = preprocess(lr, device)
    hr, _ = preprocess(hr, device)
    _, ycbcr = preprocess(bicubic, device)

    with torch.no_grad():
        preds = model(lr).clamp(0.0, 1.0)

    psnr = calc_psnr(hr, preds)
    print('PSNR: {:.2f}'.format(psnr))

    preds = preds.mul(255.0).cpu().numpy().squeeze(0).squeeze(0)

    output = np.array([preds, ycbcr[..., 1], ycbcr[..., 2]]).transpose([1, 2, 0])
    output = np.clip(convert_ycbcr_to_rgb(output), 0.0, 255.0).astype(np.uint8)
    output = pil_image.fromarray(output)
    output.save(image_path)
