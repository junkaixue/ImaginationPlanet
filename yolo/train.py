from ultralytics import YOLO
import torch

def main():
    # 验证 GPU
    print(f"CUDA 是否可用: {torch.cuda.is_available()}")
    print(f"当前 GPU: {torch.cuda.get_device_name(0)}")

    # 加载模型
    model = YOLO('yolo11n.pt')

    # 开始训练
    model.train(
        data='data.yaml',
        epochs=100,
        imgsz=640,
        batch=16,
        device=0,
        # --- 针对你的报错增加的防御性参数 ---
        amp=False,         # 关闭混合精度，防止 torchvision 的 NMS 兼容性检查
        workers=0,         # Windows 环境下设为 0 防止多线程死锁
        # --- 你的特定角度需求 ---
        degrees=0.0,
        flipud=0.0,
        fliplr=0.0
    )

if __name__ == '__main__':
    main()