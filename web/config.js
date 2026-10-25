/**
 * DataWise - Backend API Configuration
 *
 * LOCAL MODE:
 *   Leave apiBaseUrl as '' (empty string).
 *   The web application will automatically communicate with py server.py at http://127.0.0.1:8000.
 *
 * PRODUCTION / NETLIFY MODE:
 *   When hosting the frontend on Netlify, configure your separately deployed Python backend here:
 *   Example:
 *     apiBaseUrl: 'https://datawise-backend.onrender.com'
 *   
 *   Alternatively, if you use Netlify Redirects (_redirects / netlify.toml), leave apiBaseUrl as ''
 *   and Netlify will transparently proxy /api/* to your Python backend!
 */
window.DATAWISE_CONFIG = {
  // Set your deployed backend URL here if deploying frontend to Netlify:
  apiBaseUrl: ''
};
