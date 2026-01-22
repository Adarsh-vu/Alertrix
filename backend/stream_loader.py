"""
Alertrix - Video Stream Loader
Handles video capture from files and webcam using OpenCV
"""

import cv2
from typing import Union, Generator


class VideoHandler:
    """
    Video handler class for capturing frames from video files or webcam.
    
    def __init__(self, source: Union[str, int] = 0): 
        
    """
        Initialize the VideoHandler with a video source.
        
        Args:
            source: File path (str) for video file, or integer (0 for webcam)
        """
        self.source = source
        self.cap = None
        self._initialize_capture()
    
    def _initialize_capture(self) -> None:
        """Initialize the OpenCV VideoCapture object."""
        self.cap = cv2.VideoCapture(self.source)
        
        if not self.cap.isOpened():
            raise ValueError(f"Failed to open video source: {self.source}")
        
        # Set optimal buffer size for real-time streaming
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    def get_frames(self) -> Generator[bytes, None, None]:
        """
        Generator method that yields JPEG-encoded frames for streaming.
        
        Yields:
            bytes: JPEG-encoded frame data
        """
        while True:
            ret, frame = self.cap.read()
            
            if not ret:
                # If reading from file and reached end, reset to beginning
                if isinstance(self.source, str):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    break
            
            # Encode frame as JPEG
            success, encoded_frame = cv2.imencode(
                '.jpg', 
                frame, 
                [cv2.IMWRITE_JPEG_QUALITY, 85]
            )
            
            if success:
                yield encoded_frame.tobytes()
    
    def get_frame_dimensions(self) -> tuple:
        """
        Get the dimensions of the video frames.
        
        Returns:
            tuple: (width, height) of the video frames
        """
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)
    
    def get_fps(self) -> float:
        """
        Get the frames per second of the video source.
        
        Returns:
            float: FPS of the video source
        """
        return self.cap.get(cv2.CAP_PROP_FPS)
    
    def get_total_frames(self) -> int:
        """
        Get total number of frames.
        
        Returns:
            int: Total frame count, or -1 for webcam
        """
        if isinstance(self.source, str):
            return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return -1
    
    def release(self) -> None:
        """Release the video capture object."""
        if self.cap is not None:
            self.cap.release()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures resource cleanup."""
        self.release()
    
    def __del__(self):
        """Destructor - ensures resource cleanup."""
        self.release()

