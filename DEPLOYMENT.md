# Deployment Guide - COCO Backend on Render

This guide walks you through deploying your COCO backend to Render.

## Prerequisites

- Render account (sign up at https://render.com)
- GitHub repository with your code
- OpenAI API key
- ElevenLabs API key

## Step-by-Step Deployment

### 1. Push Your Code to GitHub

Make sure your latest code is pushed to GitHub:

```bash
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

### 2. Create a New Web Service on Render

1. Go to https://dashboard.render.com
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Select the `coco-backend` repository

### 3. Configure Your Service

Render will automatically detect the `render.yaml` file. Verify these settings:

- **Name**: `coco-backend` (or your preferred name)
- **Runtime**: Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Plan**: Free (or choose a paid plan for better performance)

### 4. Set Environment Variables

In the Render dashboard, add these environment variables:

```
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
FRONTEND_URL=https://your-vercel-app.vercel.app
```

**To add environment variables:**
1. Go to your service settings
2. Click "Environment" in the left sidebar
3. Add each key-value pair
4. Click "Save Changes"

### 5. Deploy

1. Click "Create Web Service"
2. Render will automatically build and deploy your application
3. Wait for the deployment to complete (usually 2-5 minutes)

### 6. Get Your Backend URL

Once deployed, Render will provide you with a URL like:
```
https://coco-backend.onrender.com
```

### 7. Update Your Vercel Frontend

Update your frontend environment variables in Vercel:

1. Go to your Vercel project settings
2. Navigate to Environment Variables
3. Add/update:
   ```
   NEXT_PUBLIC_API_URL=https://coco-backend.onrender.com
   ```
   (or whatever environment variable name you use for the backend URL)
4. Redeploy your frontend

### 8. Update CORS Settings

After you have your Vercel production URL, update the `FRONTEND_URL` environment variable in Render:

```
FRONTEND_URL=https://your-actual-vercel-url.vercel.app
```

## Testing Your Deployment

1. Visit your backend URL: `https://your-backend.onrender.com`
   - You should see: `{"status": "COCO - Conversation Coach API running (OpenAI mode)"}`

2. Test the WebSocket connection from your frontend

3. Check the Render logs for any errors:
   - Go to your service dashboard
   - Click "Logs" tab

## Important Notes

### Free Tier Limitations

If using Render's free tier:
- Service spins down after 15 minutes of inactivity
- First request after spin-down takes 30-60 seconds (cold start)
- 750 hours/month of usage

**Recommendation**: For production use with real users, consider upgrading to a paid plan ($7/month) for:
- No cold starts
- Better performance
- More resources

### WebSocket Support

Render fully supports WebSockets, which your app uses for real-time audio streaming.

### Health Checks

The `healthCheckPath: /` in `render.yaml` tells Render to ping your root endpoint to check if the service is healthy.

## Troubleshooting

### Build Fails

- Check the build logs in Render dashboard
- Verify `requirements.txt` has all dependencies
- Make sure Python version is compatible (3.11+)

### Service Won't Start

- Check that environment variables are set correctly
- Review the logs for error messages
- Verify the start command is correct

### CORS Errors

- Make sure `FRONTEND_URL` is set correctly in Render
- Check that your Vercel URL is included in CORS origins
- Note: `https://*.vercel.app` pattern allows all Vercel preview deployments

### Cold Starts (Free Tier)

- First request after inactivity takes 30-60 seconds
- Consider upgrading to paid tier or using a service like UptimeRobot to ping your app

## Monitoring

1. **Render Dashboard**: Monitor logs, metrics, and deployment status
2. **Set up alerts**: Render can notify you of deployment failures
3. **Check logs regularly**: Use the Logs tab to debug issues

## Updating Your Deployment

Render automatically redeploys when you push to your main branch:

```bash
git add .
git commit -m "Your update message"
git push origin main
```

## Alternative: Manual Deployment

If you prefer not to use `render.yaml`, you can configure everything manually in the Render dashboard when creating the service.

## Cost Estimate

- **Free Tier**: $0/month (with limitations)
- **Starter**: $7/month (recommended for production)
- **Standard**: $25/month (higher traffic)

## Support

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com
