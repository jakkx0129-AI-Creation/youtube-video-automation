import os
from PIL import Image

def resize_image(input_path, output_path, target_size=(1920, 1080)):
    with Image.open(input_path) as img:
        # Calculate aspect ratio
        img_ratio = img.width / img.height
        target_ratio = target_size[0] / target_size[1]
        
        if img_ratio > target_ratio:
            # Image is wider than target
            new_width = target_size[0]
            new_height = int(new_width / img_ratio)
        else:
            # Image is taller than target
            new_height = target_size[1]
            new_width = int(new_height * img_ratio)
            
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create a black background
        new_img = Image.new("RGB", target_size, (0, 0, 0))
        # Paste the resized image in the center
        paste_x = (target_size[0] - new_width) // 2
        paste_y = (target_size[1] - new_height) // 2
        new_img.paste(img, (paste_x, paste_y))
        
        new_img.save(output_path, "JPEG", quality=95)
        print(f"Resized: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    
    # Scan assets/ for all jpg files
    all_jpg = sorted(f for f in os.listdir(assets_dir)
                     if f.lower().endswith('.jpg') and not f.startswith('processed_'))
    
    if not all_jpg:
        print("Warning: No image files found in assets/.")
        return
    
    processed_images = []
    for i, img_name in enumerate(all_jpg):
        input_p = os.path.join(assets_dir, img_name)
        output_p = os.path.join(assets_dir, f"processed_{i+1}.jpg")
        resize_image(input_p, output_p)
        processed_images.append(output_p)
    
    if not processed_images:
        print("Warning: No image files found in assets/.")
    else:
        print(f"Successfully processed {len(processed_images)} image(s).")

if __name__ == "__main__":
    main()
