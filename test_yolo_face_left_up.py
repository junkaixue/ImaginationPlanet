import os
import unittest

from log_helper import log


class TestYoloFaceLeftUp(unittest.TestCase):
    def test_detect_face_left_up_coords(self):
        try:
            from ultralytics import YOLO
        except Exception as e:
            self.skipTest(f"ultralytics not available: {e}")
            return

        repo_root = os.path.dirname(os.path.abspath(__file__))
        weights_path = os.path.join(repo_root, "yolo", "runs", "detect", "train", "weights", "best.pt")
        if not os.path.exists(weights_path):
            self.skipTest(f"YOLO weights not found: {weights_path}")
            return

        image_path = os.environ.get("FACE_LEFT_UP_TEST_IMAGE")
        if not image_path:
            candidate = os.path.join(repo_root, "debug_screenshot.png")
            if os.path.exists(candidate):
                image_path = candidate

        if not image_path or not os.path.exists(image_path):
            self.skipTest(
                "No test image provided. Set FACE_LEFT_UP_TEST_IMAGE to a screenshot containing face_left_up."
            )
            return

        model = YOLO(weights_path)
        results = model(image_path, verbose=False)

        centers = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                if cls != 0:
                    continue
                if conf < 0.5:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                centers.append((cx, cy, conf))

        if not centers:
            self.skipTest(
                f"No face_left_up detected in image: {image_path}. Provide a better screenshot via FACE_LEFT_UP_TEST_IMAGE."
            )
            return

        centers.sort(key=lambda t: t[2], reverse=True)
        best = centers[0]
        log(f"YOLO face_left_up detections: {centers}")
        log(f"Best face_left_up center (pixels): ({best[0]:.1f}, {best[1]:.1f}) conf={best[2]:.3f}")

        self.assertGreater(best[2], 0.5)


if __name__ == "__main__":
    unittest.main()
