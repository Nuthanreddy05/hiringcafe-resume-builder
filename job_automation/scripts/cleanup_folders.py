
import shutil
from pathlib import Path

OUTPUT_ROOT = Path("/Users/nuthanreddyvaddireddy/Desktop/Google Auto")

def cleanup():
    print(f"🧹 Starting Cleanup in {OUTPUT_ROOT}")
    deleted_count = 0
    kept_count = 0
    
    for item in OUTPUT_ROOT.iterdir():
        if not item.is_dir():
            continue
            
        name = item.name
        
        # Whitelist system folders
        if name.startswith("_") or name.startswith("."):
            print(f"🛡️  Keeping System Folder: {name}")
            continue
            
        # Check for Proper Format "Company - Title"
        if " - " in name:
            print(f"✅ Keeping Proper Folder: {name}")
            kept_count += 1
        else:
            print(f"🗑️  Deleting Improper Folder: {name}")
            try:
                shutil.rmtree(item)
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting {name}: {e}")

    print(f"\n🎉 Cleanup Complete!")
    print(f"   Deleted: {deleted_count}")
    print(f"   Kept:    {kept_count}")

if __name__ == "__main__":
    cleanup()
