@echo off
echo Starting MNIST Digit Classifier...
echo.

echo Starting Flask API with HTML interface...
start "MNIST Classifier" cmd /k "python app.py"

echo.
echo Service is starting...
echo Web Interface: http://localhost:5000
echo API Endpoint: http://localhost:5000/predict
echo.
echo Press any key to exit...
pause > nul