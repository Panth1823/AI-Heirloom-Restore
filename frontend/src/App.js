import React, { useState, useCallback } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Progress } from "./components/ui/progress";
import { useToast } from "./hooks/use-toast";
import { Toaster } from "./components/ui/toaster";
import { Upload, Download, Clock, CheckCircle, XCircle, Sparkles, Image, Camera } from "lucide-react";
import "@/App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API = `${BACKEND_URL}/api`;

const PhotoUploader = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [restorationId, setRestorationId] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, uploading, processing, completed, failed
  const [progress, setProgress] = useState(0);
  const [restoredImageUrl, setRestoredImageUrl] = useState(null);
  const { toast } = useToast();

  const handleFileSelect = useCallback((event) => {
    const file = event.target.files[0];
    if (file) {
      if (file.type.startsWith('image/')) {
        setSelectedFile(file);
        const url = URL.createObjectURL(file);
        setPreviewUrl(url);
        setStatus('idle');
        setRestoredImageUrl(null);
        setRestorationId(null);
        setProgress(0);
      } else {
        toast({
          title: "Invalid File Type",
          description: "Please select an image file (JPG, PNG, etc.)",
          variant: "destructive",
        });
      }
    }
  }, [toast]);

  const uploadAndRestore = async () => {
    if (!selectedFile) return;

    try {
      setStatus('uploading');
      setProgress(20);
      
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await axios.post(`${API}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const restoration = response.data;
      setRestorationId(restoration.id);
      setStatus('processing');
      setProgress(50);

      // Poll for completion
      pollRestorationStatus(restoration.id);
      
      toast({
        title: "Upload Successful!",
        description: "Your photo is being restored with AI magic ✨",
      });

    } catch (error) {
      console.error('Upload failed:', error);
      setStatus('failed');
      toast({
        title: "Upload Failed",
        description: error.response?.data?.detail || "Failed to upload photo",
        variant: "destructive",
      });
    }
  };

  const pollRestorationStatus = async (id) => {
    try {
      const response = await axios.get(`${API}/restoration/${id}`);
      const restoration = response.data;
      
      if (restoration.status === 'completed') {
        setStatus('completed');
        setProgress(100);
        setRestoredImageUrl(`${API}/download/${id}`);
        toast({
          title: "Restoration Complete! 🎉",
          description: "Your heirloom photo has been beautifully restored",
        });
      } else if (restoration.status === 'failed') {
        setStatus('failed');
        toast({
          title: "Restoration Failed",
          description: restoration.error_message || "Something went wrong during restoration",
          variant: "destructive",
        });
      } else {
        // Still processing, poll again
        setProgress(Math.min(progress + 10, 90));
        setTimeout(() => pollRestorationStatus(id), 2000);
      }
    } catch (error) {
      console.error('Status check failed:', error);
      setStatus('failed');
      toast({
        title: "Status Check Failed",
        description: "Failed to check restoration status",
        variant: "destructive",
      });
    }
  };

  const downloadRestored = () => {
    if (restoredImageUrl) {
      window.open(restoredImageUrl, '_blank');
    }
  };

  const reset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setRestorationId(null);
    setStatus('idle');
    setProgress(0);
    setRestoredImageUrl(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50">
      {/* Header */}
      <header className="border-b border-amber-200 bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 text-white">
              <Camera className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Heirloom AI</h1>
              <p className="text-sm text-gray-600">Restore your precious memories with AI magic</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12">
        <div className="max-w-6xl mx-auto">
          
          {/* Hero Section */}
          <div className="text-center mb-12">
            <h2 className="text-5xl font-bold text-gray-900 mb-4">
              Bring Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-600 to-orange-600">Memories</span> Back to Life
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Transform your old, faded, or damaged photographs into vibrant, colorized masterpieces using cutting-edge AI restoration technology.
            </p>
          </div>

          {/* Upload Section */}
          {status === 'idle' && (
            <Card className="max-w-2xl mx-auto mb-8 border-2 border-dashed border-amber-300 bg-white/70 backdrop-blur-sm hover:border-amber-400 transition-colors">
              <CardHeader className="text-center">
                <CardTitle className="flex items-center justify-center gap-2">
                  <Upload className="w-6 h-6 text-amber-600" />
                  Upload Your Photo
                </CardTitle>
                <CardDescription>
                  Select an old photo you'd like to restore and colorize
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col items-center gap-6">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="photo-upload"
                    data-testid="photo-upload-input"
                  />
                  <label
                    htmlFor="photo-upload"
                    className="flex flex-col items-center gap-4 p-8 border-2 border-dashed border-amber-300 rounded-lg cursor-pointer hover:border-amber-400 hover:bg-amber-50/50 transition-all w-full"
                    data-testid="photo-upload-label"
                  >
                    <Image className="w-12 h-12 text-amber-500" />
                    <div className="text-center">
                      <p className="text-lg font-medium text-gray-700">Click to select a photo</p>
                      <p className="text-sm text-gray-500">JPG, PNG, or other image formats</p>
                    </div>
                  </label>
                  
                  {selectedFile && previewUrl && (
                    <div className="w-full">
                      <h3 className="text-lg font-semibold mb-3 text-gray-700">Preview:</h3>
                      <div className="relative rounded-lg overflow-hidden border-2 border-amber-200 mb-4">
                        <img 
                          src={previewUrl} 
                          alt="Preview" 
                          className="w-full h-64 object-contain bg-gray-100"
                          data-testid="image-preview"
                        />
                      </div>
                      <Button 
                        onClick={uploadAndRestore}
                        className="w-full bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white font-semibold py-3 transition-all transform hover:scale-105"
                        data-testid="restore-photo-button"
                      >
                        <Sparkles className="w-5 h-5 mr-2" />
                        Restore My Photo
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Processing Status */}
          {(status === 'uploading' || status === 'processing') && (
            <Card className="max-w-2xl mx-auto mb-8 bg-white/80 backdrop-blur-sm">
              <CardHeader className="text-center">
                <CardTitle className="flex items-center justify-center gap-2">
                  <Clock className="w-6 h-6 text-blue-600 animate-spin" />
                  {status === 'uploading' ? 'Uploading Photo...' : 'Restoring Your Memory...'}
                </CardTitle>
                <CardDescription>
                  Our AI is working its magic on your precious photo
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Progress value={progress} className="w-full" data-testid="restoration-progress" />
                  <p className="text-center text-sm text-gray-600">
                    {status === 'uploading' ? 'Uploading and analyzing your photo...' : 'Applying restoration and colorization...'}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Results Section */}
          {status === 'completed' && previewUrl && restoredImageUrl && (
            <div className="space-y-8">
              <Card className="bg-white/80 backdrop-blur-sm">
                <CardHeader className="text-center">
                  <CardTitle className="flex items-center justify-center gap-2 text-green-700">
                    <CheckCircle className="w-6 h-6" />
                    Restoration Complete!
                  </CardTitle>
                  <CardDescription>
                    Your heirloom photo has been beautifully restored
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 gap-8">
                    {/* Before */}
                    <div className="space-y-3">
                      <h3 className="text-lg font-semibold text-gray-700 text-center">Before</h3>
                      <div className="relative rounded-lg overflow-hidden border-2 border-gray-300">
                        <img 
                          src={previewUrl} 
                          alt="Original" 
                          className="w-full h-80 object-contain bg-gray-100"
                          data-testid="before-image"
                        />
                      </div>
                    </div>
                    
                    {/* After */}
                    <div className="space-y-3">
                      <h3 className="text-lg font-semibold text-gray-700 text-center">After</h3>
                      <div className="relative rounded-lg overflow-hidden border-2 border-green-300">
                        <img 
                          src={restoredImageUrl} 
                          alt="Restored" 
                          className="w-full h-80 object-contain bg-gray-100"
                          data-testid="after-image"
                        />
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex gap-4 justify-center mt-8">
                    <Button 
                      onClick={downloadRestored}
                      className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white font-semibold px-8 py-3"
                      data-testid="download-button"
                    >
                      <Download className="w-5 h-5 mr-2" />
                      Download Restored Photo
                    </Button>
                    <Button 
                      onClick={reset}
                      variant="outline"
                      className="border-2 border-amber-300 text-amber-700 hover:bg-amber-50 font-semibold px-8 py-3"
                      data-testid="restore-another-button"
                    >
                      Restore Another Photo
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Error State */}
          {status === 'failed' && (
            <Card className="max-w-2xl mx-auto mb-8 bg-red-50/80 border-red-200">
              <CardHeader className="text-center">
                <CardTitle className="flex items-center justify-center gap-2 text-red-700">
                  <XCircle className="w-6 h-6" />
                  Restoration Failed
                </CardTitle>
                <CardDescription className="text-red-600">
                  Something went wrong during the restoration process
                </CardDescription>
              </CardHeader>
              <CardContent className="text-center">
                <Button 
                  onClick={reset}
                  className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white font-semibold"
                  data-testid="try-again-button"
                >
                  Try Again
                </Button>
              </CardContent>
            </Card>
          )}

        </div>
      </main>
      <Toaster />
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PhotoUploader />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
