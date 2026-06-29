import string

import torch
import torch.backends.cudnn as cudnn
import torch.nn.functional as F
import torchvision.transforms as transforms

from deep_text_recognition_benchmark.model import Model
from deep_text_recognition_benchmark.utils import AttnLabelConverter, CTCLabelConverter


class DTRB:
    def __init__(self, weights_path, opt):
        if opt.sensitive:
            opt.character = string.printable[:-6]

        requested_device = getattr(opt, "device", "cuda")
        if requested_device == "auto":
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is required for this configuration, but no GPU is available.")
            requested_device = "cuda"
        if requested_device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA is required for this configuration, but no GPU is available.")

        self.device = torch.device(requested_device)
        self.opt = opt
        self.transform = transforms.ToTensor()
        self.use_half = bool(getattr(opt, "half", False)) and self.device.type == "cuda"

        if self.device.type == "cuda":
            cudnn.benchmark = True
            cudnn.deterministic = False
            opt.num_gpu = torch.cuda.device_count()
        else:
            cudnn.benchmark = False
            cudnn.deterministic = False
            opt.num_gpu = 0

        if "CTC" in opt.Prediction:
            self.converter = CTCLabelConverter(opt.character)
        else:
            self.converter = AttnLabelConverter(opt.character)
        opt.num_class = len(self.converter.character)

        if opt.rgb:
            opt.input_channel = 3

        self.load_model(weights_path, opt)

    def load_model(self, weights_path, opt):
        model = Model(opt)
        state_dict = torch.load(weights_path, map_location=self.device, weights_only=True)
        if any(key.startswith("module.") for key in state_dict):
            state_dict = {key.replace("module.", "", 1): value for key, value in state_dict.items()}
        model.load_state_dict(state_dict)

        if self.device.type == "cuda" and torch.cuda.device_count() > 1:
            model = torch.nn.DataParallel(model)

        self.model = model.to(self.device)
        if self.use_half:
            self.model = self.model.half()
        self.model.eval()

    def predict(self, image, opt=None):
        inference_opt = opt or self.opt
        image_tensor = self.transform(image).sub_(0.5).div_(0.5).unsqueeze(0).to(self.device)
        if self.use_half:
            image_tensor = image_tensor.half()
        batch_size = image_tensor.size(0)
        length_for_pred = torch.IntTensor([inference_opt.batch_max_length] * batch_size).to(self.device)
        text_for_pred = torch.LongTensor(batch_size, inference_opt.batch_max_length + 1).fill_(0).to(self.device)

        autocast_enabled = self.device.type == "cuda" and self.use_half
        with torch.inference_mode(), torch.autocast(device_type=self.device.type, dtype=torch.float16, enabled=autocast_enabled):
            if "CTC" in inference_opt.Prediction:
                preds = self.model(image_tensor, text_for_pred)
                preds_size = torch.IntTensor([preds.size(1)] * batch_size)
                _, preds_index = preds.max(2)
                preds_str = self.converter.decode(preds_index, preds_size)
            else:
                preds = self.model(image_tensor, text_for_pred, is_train=False)
                _, preds_index = preds.max(2)
                preds_str = self.converter.decode(preds_index, length_for_pred)

            preds_prob = F.softmax(preds, dim=2)
            preds_max_prob, _ = preds_prob.max(dim=2)

        pred = preds_str[0]
        pred_max_prob = preds_max_prob[0]

        if "Attn" in inference_opt.Prediction:
            pred_eos = pred.find("[s]")
            pred = pred[:pred_eos]
            pred_max_prob = pred_max_prob[:pred_eos]

        if pred_max_prob.numel() == 0:
            return "", 0.0

        confidence_score = float(pred_max_prob.cumprod(dim=0)[-1].item())
        return pred, confidence_score



if __name__ == "__main__":
    plate_recognizer = DTRB("../weigths/dtrb-recoginzer/dtrb-None-VGG-BiLSTM-CTC-license-plate-recognizer.pth")
    plate_recognizer.predict("../io/input/582581_556.jpg")
