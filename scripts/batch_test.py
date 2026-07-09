#!/usr/bin/env python3
"""
Batch testing script for Ski Analysis.

Usage:
    python batch_test.py --input ./test-images --output results.csv
"""
import argparse
import os
import sys
import csv
import requests
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path to import analysis modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from analysis import pose_detector, technique_analyzer


def process_image(image_path: str) -> Dict[str, Any]:
    """
    Process a single image and return analysis results.

    Args:
        image_path: Path to image file

    Returns:
        Dictionary with analysis results
    """
    try:
        # Read image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()

        # Detect pose
        pose_data = pose_detector.detect_from_file(image_bytes)

        if not pose_data:
            return {
                "filename": os.path.basename(image_path),
                "status": "failed",
                "error": "No pose detected",
                "overall_score": 0,
                "forward_lean": 0,
                "knee_flexion": 0,
                "balance": 0,
                "stance_score": 0,
                "balance_score": 0,
                "lower_body_score": 0,
                "upper_body_score": 0
            }

        # Analyze technique
        analysis_result = technique_analyzer.analyze(pose_data)

        # Extract key metrics
        metrics = analysis_result["metrics"]
        scores = analysis_result["scores"]

        return {
            "filename": os.path.basename(image_path),
            "status": "success",
            "error": "",
            "overall_score": round(scores["overall_score"], 1),
            "forward_lean": round(metrics["forward_lean_angle"], 1),
            "knee_flexion": round(metrics["avg_knee_flexion"], 1),
            "balance": round(metrics["center_of_mass"]["balance"], 1),
            "stance_score": round(scores.get("stance_score", 0), 1),
            "balance_score": round(scores.get("balance_score", 0), 1),
            "lower_body_score": round(scores.get("lower_body_score", 0), 1),
            "upper_body_score": round(scores.get("upper_body_score", 0), 1),
            "shoulder_alignment": round(metrics["shoulder_alignment"], 1),
            "num_recommendations": len(analysis_result["recommendations"]),
            "pose_quality": analysis_result["pose_quality"]
        }

    except Exception as e:
        return {
            "filename": os.path.basename(image_path),
            "status": "error",
            "error": str(e),
            "overall_score": 0,
            "forward_lean": 0,
            "knee_flexion": 0,
            "balance": 0,
            "stance_score": 0,
            "balance_score": 0,
            "lower_body_score": 0,
            "upper_body_score": 0
        }


def batch_process(input_dir: str, output_file: str):
    """
    Process all images in a directory and save results to CSV.

    Args:
        input_dir: Directory containing images
        output_file: Path to output CSV file
    """
    # Find all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    image_files = []

    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: Directory {input_dir} does not exist")
        return

    # Recursively find all images
    for ext in image_extensions:
        image_files.extend(input_path.rglob(f'*{ext}'))

    if not image_files:
        print(f"No images found in {input_dir}")
        return

    print(f"Found {len(image_files)} images to process")
    print(f"Processing...\n")

    results = []
    for idx, image_path in enumerate(image_files, 1):
        print(f"[{idx}/{len(image_files)}] Processing {image_path.name}...", end=" ")

        result = process_image(str(image_path))
        results.append(result)

        if result["status"] == "success":
            print(f"✅ Score: {result['overall_score']}")
        else:
            print(f"❌ {result['error']}")

    # Write results to CSV
    if results:
        fieldnames = [
            "filename", "status", "error",
            "overall_score", "stance_score", "balance_score",
            "lower_body_score", "upper_body_score",
            "forward_lean", "knee_flexion", "balance",
            "shoulder_alignment", "num_recommendations", "pose_quality"
        ]

        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        print(f"\n✅ Results saved to {output_file}")

        # Print summary
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful

        print(f"\n📊 Summary:")
        print(f"   Total: {len(results)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")

        if successful > 0:
            avg_score = sum(r["overall_score"] for r in results if r["status"] == "success") / successful
            print(f"   Average Score: {avg_score:.1f}")

            # Top 3
            sorted_results = sorted([r for r in results if r["status"] == "success"],
                                  key=lambda x: x["overall_score"], reverse=True)
            print(f"\n🏆 Top 3 Scores:")
            for i, r in enumerate(sorted_results[:3], 1):
                print(f"   {i}. {r['filename']}: {r['overall_score']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Batch test skiing images')
    parser.add_argument('--input', '-i', required=True,
                       help='Input directory containing images')
    parser.add_argument('--output', '-o', default='results.csv',
                       help='Output CSV file (default: results.csv)')

    args = parser.parse_args()

    print("🎿 Ski Analysis - Batch Testing")
    print("=" * 50)

    batch_process(args.input, args.output)


if __name__ == '__main__':
    main()
