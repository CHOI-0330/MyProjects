import serial
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
# 시리얼 포트 설정 (포트 이름과 보드레이트는 아두이노 설정에 맞게 변경)
ser = serial.Serial('COM6', 115200)
# 데이터 초기화
signal_data = []
timestamps = []
# 그래프 설정
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
# 실시간 데이터 업데이트 함수
def update(frame):
    global signal_data, timestamps
    if ser.in_waiting:
        line = ser.readline().decode('utf-8').strip()
        print(f"Received raw data: {line}")
        if line.startswith('Signal: '):
            try:
                signal = int(line.split('Signal: ')[1])
                signal_data.append(signal)
                timestamps.append(len(signal_data))
                # 실시간 신호 그래프 업데이트
                ax1.cla()
                ax1.plot(timestamps[-200:], signal_data[-200:])
                ax1.set_title('ECG Signal (Real-time)')
                ax1.set_xlabel('Time (samples)')
                ax1.set_ylabel('Amplitude')
                # 자기상관 함수 계산 및 그래프 업데이트
                if len(signal_data) >= 250:
                    N = 250  # 데이터 길이
                    signal_segment = signal_data[-N:]
                    autocorr = np.correlate(signal_segment - np.mean(signal_segment), signal_segment - np.mean(signal_segment), mode='full')
                    autocorr = autocorr[len(autocorr) // 2:]  # 양의 시차 부분만 사용
                    # 시차(lag) 값을 주파수(Hz)로 변환
                    T = 1.0 / 100.0  # 샘플링 주기 (초)
                    lags = np.arange(1, len(autocorr))  # 시차 0은 제외
                    frequencies = 1. / (lags * T)  # 주파수 = 1 / (시차 * 주기)
                    ax2.cla()
                    ax2.plot(frequencies, autocorr[1:])
                    ax2.set_title('Autocorrelation of ECG Signal (Frequency Domain)')
                    ax2.set_xlabel('Frequency (Hz)')
                    ax2.set_ylabel('Autocorrelation')
                    ax2.set_xlim(0, 5)  # X축 범위 설정
                    # 1.0 Hz ~ 1.6 Hz 범위에서의 극대치 찾기
                    mask = (frequencies >= 1.0) & (frequencies <= 1.6)
                    selected_frequencies = frequencies[mask]
                    selected_autocorr = autocorr[1:][mask]
                    if len(selected_frequencies) > 0:
                        peak_idx = np.argmax(selected_autocorr)
                        peak_frequency = selected_frequencies[peak_idx]
                        print(f"Peak frequency in range 1.0-1.6 Hz: {peak_frequency} Hz")
            except ValueError:
                print(f"ValueError: Could not convert '{line}' to integer.")
# 애니메이션 설정
ani = FuncAnimation(fig, update, interval=100)
plt.tight_layout()
plt.show()
# 프로그램 종료 시 시리얼 포트 닫기
ser.close()