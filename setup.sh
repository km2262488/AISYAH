```bash
#!/bin/bash
# setup.sh - Setup script for AISYAH

echo "🌸 AISYAH - Setup Script"
echo "========================"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.7"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $required_version or higher is required"
    echo "Current version: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Make script executable
chmod +x aisyah.py

echo "✅ Setup complete!"
echo "🚀 Run AISYAH: python3 aisyah.py"
```

