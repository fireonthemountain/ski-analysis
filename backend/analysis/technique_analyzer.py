"""
Technique analysis engine for skiing pose data.

Based on PSIA (Professional Ski Instructors of America) standards and
biomechanical principles for alpine skiing technique evaluation.

References:
- PSIA Alpine Technical Manual
- PSIA Core Movement Concepts
- Biomechanical Analysis of Alpine Skiing
"""
import math
from typing import Dict, List, Any, Optional, Tuple


class TechniqueAnalyzer:
    """
    Analyzes skiing technique from pose landmarks.

    Evaluates technique based on PSIA standards:
    - Stance and Balance (Forward/Aft, Lateral)
    - Lower Body Mechanics (Flexion, Alignment)
    - Upper Body Position (Stability, Separation)
    - Overall Biomechanical Efficiency

    Note: Static image analysis has limitations. Dynamic metrics
    (edge angle, pressure control, turn dynamics) require video analysis.
    """

    # MediaPipe landmark indices
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self):
        """Initialize analyzer."""
        pass

    def analyze(self, pose_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze skiing technique from pose data.

        Args:
            pose_data: Pose landmarks data

        Returns:
            Dictionary containing analysis results
        """
        landmarks = pose_data["landmarks"]

        # Calculate all metrics
        metrics = {}
        scores = {}

        # 1. Stance & Balance
        forward_lean = self._calculate_forward_lean(landmarks)
        hip_ankle_alignment = self._calculate_hip_ankle_alignment(landmarks)
        center_of_mass = self._calculate_center_of_mass(landmarks)

        metrics["forward_lean_angle"] = forward_lean
        metrics["hip_ankle_alignment"] = hip_ankle_alignment
        metrics["center_of_mass"] = center_of_mass

        scores["stance_score"] = self._score_stance(forward_lean, hip_ankle_alignment)
        scores["balance_score"] = self._score_balance(center_of_mass)

        # 2. Lower Body
        left_knee_flex = self._calculate_knee_flexion(landmarks, "left")
        right_knee_flex = self._calculate_knee_flexion(landmarks, "right")
        avg_knee_flex = (left_knee_flex + right_knee_flex) / 2

        metrics["left_knee_flexion"] = left_knee_flex
        metrics["right_knee_flexion"] = right_knee_flex
        metrics["avg_knee_flexion"] = avg_knee_flex

        scores["lower_body_score"] = self._score_knee_flexion(avg_knee_flex)

        # 3. Upper Body
        shoulder_alignment = self._calculate_shoulder_alignment(landmarks)
        metrics["shoulder_alignment"] = shoulder_alignment
        scores["upper_body_score"] = self._score_upper_body(shoulder_alignment)

        # 4. Overall Score
        scores["overall_score"] = self._calculate_overall_score(scores)

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, scores)

        return {
            "metrics": metrics,
            "scores": scores,
            "recommendations": recommendations,
            "pose_quality": self._assess_pose_quality(landmarks)
        }

    def _get_landmark(self, landmarks: List[Dict], idx: int) -> Optional[Dict]:
        """Get landmark by index."""
        for lm in landmarks:
            if lm["id"] == idx:
                return lm
        return None

    def _calculate_distance(self, p1: Dict, p2: Dict) -> float:
        """Calculate Euclidean distance between two points."""
        dx = p2["x"] - p1["x"]
        dy = p2["y"] - p1["y"]
        return math.sqrt(dx * dx + dy * dy)

    def _calculate_angle(self, p1: Dict, p2: Dict, p3: Dict) -> float:
        """
        Calculate angle at p2 formed by p1-p2-p3.
        Returns angle in degrees.
        """
        # Vectors
        v1 = (p1["x"] - p2["x"], p1["y"] - p2["y"])
        v2 = (p3["x"] - p2["x"], p3["y"] - p2["y"])

        # Dot product and magnitudes
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)

        if mag1 == 0 or mag2 == 0:
            return 0

        # Angle in radians then degrees
        cos_angle = dot / (mag1 * mag2)
        cos_angle = max(-1, min(1, cos_angle))  # Clamp to [-1, 1]
        angle_rad = math.acos(cos_angle)
        return math.degrees(angle_rad)

    def _calculate_forward_lean(self, landmarks: List[Dict]) -> float:
        """Calculate forward lean angle in degrees."""
        hip_center = self._get_hip_center(landmarks)
        ankle_center = self._get_ankle_center(landmarks)
        shoulder_center = self._get_shoulder_center(landmarks)

        if not all([hip_center, ankle_center, shoulder_center]):
            return 0

        # Calculate angle from vertical
        # Positive = leaning forward, Negative = leaning back
        dx = shoulder_center["x"] - ankle_center["x"]
        dy = shoulder_center["y"] - ankle_center["y"]

        if dy == 0:
            return 0

        angle = math.degrees(math.atan(dx / abs(dy)))
        return angle

    def _calculate_hip_ankle_alignment(self, landmarks: List[Dict]) -> float:
        """Calculate horizontal distance between hip and ankle centers."""
        hip_center = self._get_hip_center(landmarks)
        ankle_center = self._get_ankle_center(landmarks)

        if not all([hip_center, ankle_center]):
            return 0

        return abs(hip_center["x"] - ankle_center["x"])

    def _calculate_center_of_mass(self, landmarks: List[Dict]) -> Dict[str, float]:
        """Estimate center of mass (approximated as hip center)."""
        hip_center = self._get_hip_center(landmarks)
        ankle_center = self._get_ankle_center(landmarks)

        if not all([hip_center, ankle_center]):
            return {"x": 0.5, "y": 0.5, "balance": 50}

        # Balance score: how centered COM is over feet
        lateral_offset = abs(hip_center["x"] - ankle_center["x"])
        balance_score = max(0, 100 - (lateral_offset * 500))  # Scale to 0-100

        return {
            "x": hip_center["x"],
            "y": hip_center["y"],
            "balance": balance_score
        }

    def _calculate_knee_flexion(self, landmarks: List[Dict], side: str) -> float:
        """Calculate knee flexion angle."""
        if side == "left":
            hip = self._get_landmark(landmarks, self.LEFT_HIP)
            knee = self._get_landmark(landmarks, self.LEFT_KNEE)
            ankle = self._get_landmark(landmarks, self.LEFT_ANKLE)
        else:
            hip = self._get_landmark(landmarks, self.RIGHT_HIP)
            knee = self._get_landmark(landmarks, self.RIGHT_KNEE)
            ankle = self._get_landmark(landmarks, self.RIGHT_ANKLE)

        if not all([hip, knee, ankle]):
            return 0

        return self._calculate_angle(hip, knee, ankle)

    def _calculate_shoulder_alignment(self, landmarks: List[Dict]) -> float:
        """Calculate shoulder tilt angle from horizontal."""
        left_shoulder = self._get_landmark(landmarks, self.LEFT_SHOULDER)
        right_shoulder = self._get_landmark(landmarks, self.RIGHT_SHOULDER)

        if not all([left_shoulder, right_shoulder]):
            return 0

        dy = right_shoulder["y"] - left_shoulder["y"]
        dx = right_shoulder["x"] - left_shoulder["x"]

        if dx == 0:
            return 0

        angle = math.degrees(math.atan(dy / dx))
        return abs(angle)

    def _get_hip_center(self, landmarks: List[Dict]) -> Optional[Dict]:
        """Get center point between hips."""
        left_hip = self._get_landmark(landmarks, self.LEFT_HIP)
        right_hip = self._get_landmark(landmarks, self.RIGHT_HIP)

        if not all([left_hip, right_hip]):
            return None

        return {
            "x": (left_hip["x"] + right_hip["x"]) / 2,
            "y": (left_hip["y"] + right_hip["y"]) / 2
        }

    def _get_ankle_center(self, landmarks: List[Dict]) -> Optional[Dict]:
        """Get center point between ankles."""
        left_ankle = self._get_landmark(landmarks, self.LEFT_ANKLE)
        right_ankle = self._get_landmark(landmarks, self.RIGHT_ANKLE)

        if not all([left_ankle, right_ankle]):
            return None

        return {
            "x": (left_ankle["x"] + right_ankle["x"]) / 2,
            "y": (left_ankle["y"] + right_ankle["y"]) / 2
        }

    def _get_shoulder_center(self, landmarks: List[Dict]) -> Optional[Dict]:
        """Get center point between shoulders."""
        left_shoulder = self._get_landmark(landmarks, self.LEFT_SHOULDER)
        right_shoulder = self._get_landmark(landmarks, self.RIGHT_SHOULDER)

        if not all([left_shoulder, right_shoulder]):
            return None

        return {
            "x": (left_shoulder["x"] + right_shoulder["x"]) / 2,
            "y": (left_shoulder["y"] + right_shoulder["y"]) / 2
        }

    def _score_stance(self, forward_lean: float, alignment: float) -> float:
        """
        Score stance quality (0-100).

        PSIA Standard: Athletic stance with shin pressure on boot tongue.
        Forward lean of 15-25° indicates proper pressure distribution
        and readiness for terrain absorption.

        Too far back (<10°): "Backseat" skiing - common beginner issue
        Too far forward (>30°): Over-pressuring tips, loss of control
        """
        # Ideal forward lean: 15-25 degrees (PSIA recommended)
        lean_score = 0
        if 15 <= forward_lean <= 25:
            lean_score = 100  # Optimal PSIA range
        elif 10 <= forward_lean < 15 or 25 < forward_lean <= 30:
            lean_score = 75   # Acceptable, room for improvement
        elif 5 <= forward_lean < 10 or 30 < forward_lean <= 35:
            lean_score = 50   # Noticeable issue
        else:
            lean_score = 25   # Significant problem

        # Ideal alignment: close to vertical (< 0.05)
        # PSIA: Hips should stack over ankles for balance
        alignment_score = max(0, 100 - (alignment * 1000))

        return (lean_score * 0.6 + alignment_score * 0.4)

    def _score_balance(self, com: Dict[str, float]) -> float:
        """
        Score balance (0-100).

        PSIA Standard: Center of mass should be centered over base of support.
        Proper balance allows for dynamic movements and quick adjustments.
        """
        return com["balance"]

    def _score_knee_flexion(self, angle: float) -> float:
        """
        Score knee flexion (0-100).

        PSIA Standard: Athletic stance requires flexed knees for:
        - Shock absorption
        - Terrain adaptation
        - Quick pressure changes
        - Dynamic balance

        140-160° angle = 20-40° of flexion (ideal)
        >170° = Locked/straight knees (common error)
        <130° = Over-flexed (reduces power and control)
        """
        # Ideal: 20-40 degrees flexion (140-160 degree angle)
        if 140 <= angle <= 160:
            return 100  # PSIA optimal range
        elif 130 <= angle < 140 or 160 < angle <= 170:
            return 75   # Acceptable
        elif 120 <= angle < 130 or 170 < angle <= 175:
            return 50   # Needs work
        else:
            return 25   # Significant issue

    def _score_upper_body(self, shoulder_tilt: float) -> float:
        """
        Score upper body position (0-100).

        PSIA Standard: Level shoulders facing down fall line.
        Upper/lower body separation is key for:
        - Edge control
        - Balance
        - Rotary control
        - Clean carving

        Tilted shoulders indicate rotation (common intermediate error).
        """
        # Ideal: shoulders level (< 5 degrees tilt)
        if shoulder_tilt < 5:
            return 100  # Excellent separation
        elif shoulder_tilt < 10:
            return 80   # Good
        elif shoulder_tilt < 15:
            return 60   # Room for improvement
        else:
            return 40   # Rotation issue

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted overall score."""
        weights = {
            "stance_score": 0.3,
            "balance_score": 0.25,
            "lower_body_score": 0.25,
            "upper_body_score": 0.2
        }

        total = sum(scores.get(key, 0) * weight for key, weight in weights.items())
        return round(total, 1)

    def _generate_recommendations(
        self,
        metrics: Dict[str, float],
        scores: Dict[str, float]
    ) -> List[Dict[str, str]]:
        """Generate coaching recommendations."""
        recommendations = []

        # Forward lean
        forward_lean = metrics.get("forward_lean_angle", 0)
        if forward_lean < 10:
            recommendations.append({
                "category": "Stance",
                "issue": "Sitting back",
                "suggestion": "Lean forward more from your ankles, not your waist. Keep shins pressed against boot tongues.",
                "priority": "high"
            })
        elif forward_lean > 30:
            recommendations.append({
                "category": "Stance",
                "issue": "Too far forward",
                "suggestion": "Reduce forward lean slightly. You may be over-pressing the fronts of your skis.",
                "priority": "medium"
            })

        # Knee flexion
        avg_knee_flex = metrics.get("avg_knee_flexion", 0)
        if avg_knee_flex > 170:
            recommendations.append({
                "category": "Lower Body",
                "issue": "Knees too straight",
                "suggestion": "Flex your knees more to maintain an athletic stance and absorb terrain.",
                "priority": "high"
            })
        elif avg_knee_flex < 130:
            recommendations.append({
                "category": "Lower Body",
                "issue": "Over-flexed knees",
                "suggestion": "Stand up slightly. Over-flexing can reduce power and control.",
                "priority": "medium"
            })

        # Balance
        balance_score = scores.get("balance_score", 0)
        if balance_score < 60:
            recommendations.append({
                "category": "Balance",
                "issue": "Off-center balance",
                "suggestion": "Center your weight over your feet. Practice balancing drills on flat terrain.",
                "priority": "high"
            })

        # Shoulder alignment
        shoulder_tilt = metrics.get("shoulder_alignment", 0)
        if shoulder_tilt > 10:
            recommendations.append({
                "category": "Upper Body",
                "issue": "Tilted shoulders",
                "suggestion": "Keep shoulders level and facing downhill. Avoid leaning into turns with your upper body.",
                "priority": "medium"
            })

        # If everything looks good
        if not recommendations:
            recommendations.append({
                "category": "Overall",
                "issue": "Good technique!",
                "suggestion": "Your form looks solid. Focus on maintaining this position while skiing dynamically.",
                "priority": "low"
            })

        return recommendations

    def _assess_pose_quality(self, landmarks: List[Dict]) -> str:
        """Assess quality of pose detection."""
        # Check visibility of key landmarks
        key_indices = [
            self.LEFT_SHOULDER, self.RIGHT_SHOULDER,
            self.LEFT_HIP, self.RIGHT_HIP,
            self.LEFT_KNEE, self.RIGHT_KNEE,
            self.LEFT_ANKLE, self.RIGHT_ANKLE
        ]

        visible_count = 0
        for idx in key_indices:
            lm = self._get_landmark(landmarks, idx)
            if lm and lm.get("visibility", 0) > 0.5:
                visible_count += 1

        visibility_ratio = visible_count / len(key_indices)

        if visibility_ratio > 0.9:
            return "excellent"
        elif visibility_ratio > 0.75:
            return "good"
        elif visibility_ratio > 0.5:
            return "fair"
        else:
            return "poor"


# Singleton instance
technique_analyzer = TechniqueAnalyzer()
