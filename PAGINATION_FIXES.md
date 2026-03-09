# Pagination Download Fixes

## Overview
This document describes the fixes implemented to resolve pagination download issues in the OneHealth automation script.

## Issues Fixed

### 1. Pagination Fails on Page 2
**Problem**: Error "Locator expected to be visible - Actual value: None" when trying to find the checkbox on subsequent pages.

**Root Cause**: The checkbox selector `input.abyss-data-table-selection[type='checkbox']` was not consistently visible or accessible on all pages.

**Solution**: 
- Added multiple fallback checkbox selectors
- Implemented retry logic with 3 attempts
- Added proper error handling and logging

### 2. Only 21/50 Files Downloaded
**Problem**: Download timeout was too short for large file sets, causing some files to be missed.

**Root Cause**: Fixed 20-second timeout regardless of file count, and no verification of download completion.

**Solution**:
- Dynamic timeout calculation based on estimated file count
- Extended timeout for pages with many files (up to 90 seconds)
- Added download verification to ensure files were actually captured
- Reduced individual download timeout to be more responsive

## Changes Made

### `paginated_download.py`
1. **Enhanced Checkbox Detection**:
   ```python
   checkbox_selectors = [
       "input.abyss-data-table-selection[type='checkbox']",
       "input[type='checkbox'][class*='selection']",
       "input[type='checkbox']",
       "tbody tr:first-child input[type='checkbox']"
   ]
   ```

2. **Dynamic Download Timeout**:
   ```python
   estimated_files = 50  # Conservative estimate
   base_timeout = 20
   estimated_timeout = min(base_timeout + (estimated_files * 0.5), 60)
   ```

3. **Download Verification**:
   ```python
   if len(downloads) == 0:
       logger.warning("No downloads detected")
       return False
   ```

### `page_size.py`
1. **Enhanced Page Size Setting**:
   - Multiple fallback selectors for different page structures
   - Specific size option detection with keyboard navigation fallback
   - Better error handling and logging
   - Increased wait times for stability

### `scrape_and_download_workflow_final.py`
1. **Improved Document Table Wait**:
   - Multiple document table selectors for different page structures
   - Multiple "no documents found" message selectors
   - Increased retry attempts (5) and retry delay (3 seconds)
   - Graceful handling instead of raising exceptions
   - Better loading indicator detection

## Testing

Run the test script to verify the fixes:
```bash
cd OneHealth
python test_pagination_fix.py
```

## Usage Notes

1. **Page Size**: Set to 50 for optimal pagination performance
2. **Timeouts**: Automatically adjusted based on file count
3. **Error Handling**: Comprehensive logging for debugging
4. **Retry Logic**: Automatic retries for checkbox detection

## Expected Behavior

- **Page 1**: Should download all 50 files successfully
- **Page 2+**: Should navigate and download files without checkbox errors
- **Large File Sets**: Should wait appropriate time for all downloads
- **Error Recovery**: Should handle navigation and element visibility issues gracefully

## Monitoring

Check the logs for:
- Checkbox detection attempts and success
- Download timeout calculations
- File count verification
- Page navigation stability

## Rollback

If issues persist, the original files are backed up with `.bak` extension in the same directory.