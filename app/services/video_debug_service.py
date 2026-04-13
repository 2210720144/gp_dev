from app.models.video import Video

class VideoDebugService:
    """
    用于调试视频URL的服务类
    """
    @staticmethod
    def debug_video_urls():
        """
        打印所有视频的URL信息
        """
        # 注意：此方法需要在应用上下文中调用
        videos = Video.query.all()
        print("-" * 50)
        print(f"{'ID':<5} | {'Name':<20} | {'URL':<50} | {'Camera ID'}")
        print("-" * 50)
        for v in videos:
            # 处理可能的None值
            video_name = v.video_name if v.video_name else "N/A"
            video_url = v.video_url if v.video_url else "N/A"
            camera_id = v.camera_id if v.camera_id else "N/A"
            
            print(f"{v.video_id:<5} | {video_name:<20} | {video_url:<50} | {camera_id}")
        print("-" * 50)