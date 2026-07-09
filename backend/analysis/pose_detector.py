"""
Pose detection service using MediaPipe.
"""
import cv2
import numpy as np
import mediapipe as mp
from typing import Optional, Dict, List, Any
from PIL import Image
import io


class PoseDetector:
    """Detects human pose from images using MediaPipe."""

    def __init__(self):
        """Initialize MediaPipe Pose."""
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # Initialize pose detection
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=2,  # 0, 1, or 2. Higher = more accurate but slower
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def detect_from_file(self, file_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Detect pose from image file bytes.

        Args:
            file_bytes: Image file as bytes

        Returns:
            Dictionary containing pose landmarks and metadata, or None if no pose detected
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(file_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return None

            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Process image
            results = self.pose.process(image_rgb)

            if not results.pose_landmarks:
                return None

            # Extract landmarks
            landmarks = []
            for idx, landmark in enumerate(results.pose_landmarks.landmark):
                landmarks.append({
                    "id": idx,
                    "name": self.mp_pose.PoseLandmark(idx).name,
                    "x": landmark.x,  # Normalized [0, 1]
                    "y": landmark.y,  # Normalized [0, 1]
                    "z": landmark.z,  # Depth (relative to hips)
                    "visibility": landmark.visibility  # Confidence [0, 1]
                })

            # Get image dimensions
            height, width, _ = image.shape

            return {
                "landmarks": landmarks,
                "image_width": width,
                "image_height": height,
                "pose_detected": True,
                "num_landmarks": len(landmarks)
            }

        except Exception as e:
            print(f"Error detecting pose: {e}")
            return None

    def draw_landmarks(
        self,
        image_bytes: bytes,
        landmarks_data: Dict[str, Any]
    ) -> Optional[bytes]:
        """
        Draw pose landmarks on image.

        Args:
            image_bytes: Original image as bytes
            landmarks_data: Pose landmarks data from detect_from_file

        Returns:
            Image with drawn landmarks as bytes, or None on error
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return None

            # Convert BGR to RGB for MediaPipe
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Reconstruct MediaPipe landmarks
            landmarks = landmarks_data["landmarks"]
            pose_landmarks = self.mp_pose.PoseLandmark

            # Create landmark list for drawing
            from mediapipe.framework.formats import landmark_pb2

            landmark_list = landmark_pb2.NormalizedLandmarkList()
            for lm in landmarks:
                landmark = landmark_list.landmark.add()
                landmark.x = lm["x"]
                landmark.y = lm["y"]
                landmark.z = lm["z"]
                landmark.visibility = lm["visibility"]

            # Draw landmarks
            self.mp_drawing.draw_landmarks(
                image_rgb,
                landmark_list,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )

            # Convert back to BGR for encoding
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

            # Encode to JPEG
            success, encoded_image = cv2.imencode('.jpg', image_bgr)

            if not success:
                return None

            return encoded_image.tobytes()

        except Exception as e:
            print(f"Error drawing landmarks: {e}")
            return None

    def close(self):
        """Clean up resources."""
        if self.pose:
            self.pose.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance
pose_detector = PoseDetector()
