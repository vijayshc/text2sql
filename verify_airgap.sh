#!/bin/bash
echo "=== Air Gap Verification ==="
echo "Checking for external URLs in templates..."

if grep -r "https://" templates/ --include="*.html" | grep -v "vendor/"; then
    echo "⚠ Warning: Found external URLs in templates"
    exit 1
else
    echo "✅ No external URLs found in templates"
fi

echo "Checking vendor assets..."
VENDOR_FILES=$(find static/vendor -type f | wc -l)
if [ "$VENDOR_FILES" -gt 20 ]; then
    echo "✅ Vendor assets present ($VENDOR_FILES files)"
else
    echo "⚠ Warning: Few vendor assets found ($VENDOR_FILES files)"
fi

echo "✅ Air gap verification complete"
