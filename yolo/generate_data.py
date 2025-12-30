import cv2
import numpy as np
import os
import random

# --- 配置 ---
TEMPLATE_FILE = 'face_up_left.png'
# 建议使用绝对路径或确保文件夹存在
BG_DIR = os.path.join(os.getcwd(), 'backgrounds')
OUT_DIR = os.path.join(os.getcwd(), 'datasets/train')
COUNT = 500


def add_random_occlusion(image, x, y, tw, th):
    # 随机决定是否增加遮挡 (比如 50% 概率)
    if random.random() > 0.5:
        # 随机遮挡的大小 (目标大小的 20% 到 50%)
        occ_w = random.randint(int(tw * 0.2), int(tw * 0.5))
        occ_h = random.randint(int(th * 0.2), int(th * 0.5))

        # 随机位置 (在目标区域内或边缘)
        ox = x + random.randint(0, tw - occ_w)
        oy = y + random.randint(0, th - occ_h)

        # 模拟“半透明建筑”：取一个灰色或蓝色的矩形，设置 0.5 的透明度
        overlay = image.copy()
        cv2.rectangle(overlay, (ox, oy), (ox + occ_w, oy + occ_h), (200, 200, 200), -1)

        # 混合原图与遮挡色块
        cv2.addWeighted(overlay, 0.4, image, 0.6, 0, image)
    return image

def generate():
    # 检查模板是否存在
    if not os.path.exists(TEMPLATE_FILE):
        print(f"错误: 找不到模板文件 {TEMPLATE_FILE}")
        return

    # 检查背景文件夹是否存在
    if not os.path.exists(BG_DIR):
        os.makedirs(BG_DIR)
        print(f"错误: 背景文件夹 {BG_DIR} 是新创建的，里面没图！请放几张截图进去。")
        return

    # 获取背景图列表 (支持大小写后缀)
    bg_list = [os.path.join(BG_DIR, f) for f in os.listdir(BG_DIR)
               if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    print(f"找到背景图数量: {len(bg_list)}")

    if len(bg_list) == 0:
        print(f"错误: 在 {BG_DIR} 文件夹里没找到任何图片！")
        return

    # --- 以下是之前的逻辑 ---
    tp = cv2.imread(TEMPLATE_FILE)
    h, w = tp.shape[:2]

    os.makedirs(f"{OUT_DIR}/images", exist_ok=True)
    os.makedirs(f"{OUT_DIR}/labels", exist_ok=True)

    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(mask, (3, 3), (w - 3, h - 3), 255, -1)
    mask = cv2.GaussianBlur(mask, (11, 11), 0) / 255.0
    mask = np.stack([mask] * 3, axis=2)

    for i in range(COUNT):
        bg_path = random.choice(bg_list)
        bg = cv2.imread(bg_path)
        if bg is None:
            continue  # 防止某些图片损坏导致崩溃

        bg_h, bg_w = bg.shape[:2]

        # 色彩增强
        alpha = random.uniform(0.7, 1.3)
        beta = random.randint(-30, 30)
        tp_aug = cv2.convertScaleAbs(tp, alpha=alpha, beta=beta)

        # 随机缩放
        s = random.uniform(0.9, 1.1)
        tw, th = int(w * s), int(h * s)
        tp_resized = cv2.resize(tp_aug, (tw, th))
        mask_resized = cv2.resize(mask, (tw, th))

        # 随机位置
        x = random.randint(0, bg_w - tw)
        y = random.randint(0, bg_h - th)

        # 融合
        roi = bg[y:y + th, x:x + tw].astype(float)
        tp_part = tp_resized.astype(float)
        blended = roi * (1 - mask_resized) + tp_part * mask_resized
        bg[y:y + th, x:x + tw] = blended.astype(np.uint8)

        bg = add_random_occlusion(bg, x, y, tw, th)

        # 保存
        img_name = f"gen_{i}.jpg"
        cv2.imwrite(f"{OUT_DIR}/images/{img_name}", bg)

        cx = (x + tw / 2) / bg_w
        cy = (y + th / 2) / bg_h
        nw = tw / bg_w
        nh = th / bg_h
        with open(f"{OUT_DIR}/labels/gen_{i}.txt", 'w') as f:
            f.write(f"0 {cx} {cy} {nw} {nh}")

    print(f"✅ 成功生成 {COUNT} 张训练图，存放在: {OUT_DIR}")


if __name__ == "__main__":
    generate()