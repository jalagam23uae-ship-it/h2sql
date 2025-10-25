$form = @{
    file = Get-Item 'D:\testing-files\customers.csv'
    project_id = '22'
}

Write-Host "Uploading customers.csv to project 22..."
try {
    $response = Invoke-RestMethod -Uri 'http://localhost:11901/h2s/data-upload/upload' -Method Post -Form $form
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host "Response:"
    $response | ConvertTo-Json -Depth 5
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails) {
        Write-Host "Details: $($_.ErrorDetails.Message)"
    }
}
