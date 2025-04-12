# Error Corrections Log

## 1. AI Response JSON Parsing Error (March 18, 2025)

### Error 

### Files Changed
- `utils.py`: Added improved JSON parsing logic
- `routes/assessments.py`: Added better error handling for question creation

### Notes
- This fix handles both raw JSON responses and markdown-formatted responses from the AI
- Added logging to help diagnose future JSON parsing issues
- Improved error messages for better debugging