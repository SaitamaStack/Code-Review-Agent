# Assets Folder

Place application icons here for the build process.

## Required Files

### Windows
- `app.ico` - Windows icon file
  - Recommended: Multi-resolution (16x16, 32x32, 48x48, 256x256)
  - Tools: GIMP, Inkscape, or online converters

### macOS  
- `app.icns` - macOS icon file
  - Create using `iconutil` from an `.iconset` folder
  - Sizes needed: 16, 32, 128, 256, 512 (plus @2x versions)

### Linux
- `app.png` - PNG icon
  - Recommended: 256x256 or 512x512

## Creating Icons

### Quick Method (Online)
1. Create a 512x512 PNG image
2. Use [ConvertICO](https://convertico.com/) to create .ico
3. Use [CloudConvert](https://cloudconvert.com/png-to-icns) for .icns

### Professional Method
1. Design in vector format (SVG)
2. Export at multiple resolutions
3. Use platform-specific tools to package

## Icon Ideas for Code Review Tool
- Magnifying glass with code brackets `<>`
- Document with checkmark ✓
- Code editor with magnifying glass overlay
- Abstract representation of code analysis

## After Adding Icons

Update `code_review_agent.spec`:

```python
# Uncomment the appropriate line in EXE():
icon='assets/app.ico',  # Windows
# icon='assets/app.icns',  # macOS
```

Then rebuild: `pyinstaller code_review_agent.spec --clean`
