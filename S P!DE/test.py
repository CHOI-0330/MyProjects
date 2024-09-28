import serial
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.animation import FuncAnimation
# 시리얼 포트 설정 (포트 이름과 보드레이트는 아두이노 설정에 맞게 변경)
ser = serial.Serial('/dev/tty.ESP32_Bluetooth', 4800)  # COM5는 윈도우 예시, Mac/리눅스는 '/dev/tty.*'
# 데이터 초기화
data = pd.DataFrame(columns=['Timestamp', 'Signal'])
# 실시간 데이터 업데이트 함수
def update_data(new_signal):
    timestamp = pd.Timestamp.now()
    global data
    new_data = pd.DataFrame({'Timestamp': [timestamp], 'Signal': [new_signal]})
    data = pd.concat([data, new_data], ignore_index=True)
    # 디버깅: 데이터 확인
    print(f"Data updated: {timestamp}, {new_signal}")
# 그래프 업데이트 함수
def animate(i):
    if ser.in_waiting:  # 수신된 데이터가 있으면
        line = ser.readline().decode('utf-8').strip()  # 데이터 읽기
        print(f"Received raw data: {line}")  # 디버깅: 원시 데이터 확인
        if line.startswith('Signal: '):
            try:
                new_signal = int(line.split('Signal: ')[1])  # 'Signal: ' 이후의 숫자 추출
                update_data(new_signal)  # 데이터 업데이트
            except ValueError:
                print(f"ValueError: Could not convert '{line}' to integer.")  # 디버깅: 오류 확인
    plt.cla()
    if len(data) > 1:  # 데이터가 충분히 쌓였을 때
        # 신호 추출 및 FFT 계산
        signal = data['Signal'].values.astype(float)  # 데이터 타입을 float로 변환
        N = len(signal)
        T = 1.0  # 샘플링 주기 (초 단위)
        x = np.linspace(0.0, N*T, N, endpoint=False)
        yf = np.fft.fft(signal)
        xf = np.fft.fftfreq(N, T)
        # FFT 결과 그래프
        plt.subplot(2, 1, 1)
        plt.plot(x, signal)
        plt.xlabel('Time')
        plt.ylabel('Signal')
        plt.title('Real-time Signal Plot')
        plt.subplot(2, 1, 2)
        plt.plot(xf[:N//2], np.abs(yf[:N//2]))  # 양의 주파수 성분만 표시
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Magnitude')
        plt.title('FFT of Signal')
    else:
        plt.text(0.5, 0.5, 'No data yet', horizontalalignment='center', verticalalignment='center')
# 그래프 설정
fig, ax = plt.subplots(2, 1, figsize=(10, 6))
ani = FuncAnimation(fig, animate, interval=10)  # 1초마다 업데이트
plt.tight_layout()
plt.show()
# 프로그램 종료 시 시리얼 포트 닫기
ser.close()
