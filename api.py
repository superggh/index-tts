from flask import Flask, request, jsonify, make_response
from indextts.infer import IndexTTS
import subprocess
import os,requests,wget,json,sys

app = Flask(__name__)

# 初始化 IndexTTS
tts = IndexTTS(model_dir="checkpoints", cfg_path="checkpoints/config.yaml")
ffmpeg_path = os.path.join('ffmpeg', 'ffmpeg')
# 用于记录当前文件名编号
current_index = 1


def showErr(e):
    response = jsonify({"error": e})
    response = make_response(response)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response, 400

def getDownloadModelUrl(model_name,uid):
    url = 'https://api.angula.net/AiMan/getModelUrlByUid'
    headers = {'Content-Type': 'application/json'}
    payload ={
         "model_name":model_name,
         "uid":uid
    }
    timeout = (connect_timeout, read_timeout) = (5,120)
    try:
        r = requests.post(url,data=json.dumps(payload),headers=headers, timeout =timeout)
 
        print(r.text)
        result = r.json()
        if (result['code'] == 0):
                return (result['data'])
        else:
            return None
    except Exception as e:
            print(f'上传过程中出现错误: {e}')
            return None

 

@app.route('/tts', methods=['POST'])
def tts_api():
    global current_index
    data = request.get_json()
    print(data)
    speaker_filename = data.get('speaker', '')
    if not speaker_filename:
            return showErr("未提供 speaker 参数")
    text = data.get('text', '')
    model_name = data.get('model_name', '')
    uid = data.get('uid', '')
    speed = data.get('speed', 1.0)
    speaker_path = os.path.join('speaker', speaker_filename)
    if not os.path.exists(speaker_path):
        print('下载model',model_name,uid)
        model_url = getDownloadModelUrl(model_name,uid)
        print(model_url)
        if model_url:
            try:
                wget.download(model_url, speaker_path)
            except Exception as e:
                print(f"下载文件时出错: {e}")
                return ''
        else:
            return showErr(f"speaker 文件 {speaker_filename} 在 speaker 目录下不存在,且下载失败") 

        #
    try:
        # 生成输出文件名
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file = os.path.join(output_dir, f"{current_index}.wav")
        output_speed_file = os.path.join(output_dir, f"{current_index}_speed.wav")

        # 如果文件存在则删除
        if os.path.exists(output_file):
            os.remove(output_file)
        if os.path.exists(output_speed_file):
            os.remove(output_speed_file)

        current_index = (current_index % 200) + 1

        # 执行 TTS 推理
        tts.infer_fast(speaker_path, text, output_file,True)
        if not os.path.exists(output_file):
            return showErr(f"TTS 生成的音频文件 {output_file} 不存在。")
        # 根据 speed 值决定是否加速音频
        if speed != 1.0:
            try:
                # 使用 ffmpeg 加速并指定输出到 output 文件夹
                subprocess.run(
                    [ffmpeg_path, '-i', output_file, '-filter:a', f'atempo={speed}', output_speed_file],
                    check=True
                )
                # if os.path.exists(output_file):
                #     os.remove(output_file)
                final_output_file = output_speed_file
            except subprocess.CalledProcessError as ffmpeg_error:
                return showErr(f"使用 ffmpeg 加速语音时出错: {str(ffmpeg_error)}")
            
         
        else:
            final_output_file = output_file

        return {'message': 'TTS and speed adjustment successful', 'output_file': os.path.abspath(final_output_file)}
    except Exception as e:
        return {'error': str(e)}, 500


if __name__ == '__main__':
    app.run(debug=True)
    