@echo off
chcp 65001 >nul
set FFMPEG_PATH="D:\Program\FFmpeg\bin\ffmpeg.exe"

:: 自动查找当前目录下的video.m4s和audio.m4s
if exist "video.m4s" (
    if exist "audio.m4s" (
        echo 正在合并音视频...
        %FFMPEG_PATH% -i video.m4s -i audio.m4s -c:v copy -c:a copy output.mp4 -y
        if errorlevel 1 (
            echo 合并失败！可能是文件头包含无效的00字节，尝试修复...
            powershell -command "$v=[IO.File]::ReadAllBytes('video.m4s'); $v=$v | ? {$_ -ne 0}; [IO.File]::WriteAllBytes('video_fixed.m4s', $v)"
            powershell -command "$a=[IO.File]::ReadAllBytes('audio.m4s'); $a=$a | ? {$_ -ne 0}; [IO.File]::WriteAllBytes('audio_fixed.m4s', $a)"
            %FFMPEG_PATH% -i video_fixed.m4s -i audio_fixed.m4s -c copy output.mp4 -y
            if exist output.mp4 (
                echo 修复并合并成功！输出文件：output.mp4
                del /q video_fixed.m4s audio_fixed.m4s
            ) else (
                echo 修复失败，请手动用十六进制编辑器删除文件开头的00字节
            )
        ) else (
            echo 合并成功！输出文件：output.mp4
        )
    ) else (
        echo 未找到audio.m4s文件！
    )
) else (
    echo 未找到video.m4s文件！
)
pause