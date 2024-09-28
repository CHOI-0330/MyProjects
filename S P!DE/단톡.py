import serial
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
import requests
import time

# 시리얼 포트 설정 (포트 이름과 보드레이트는 아두이노 설정에 맞게 변경)
ser = serial.Serial('COM6', 115200)

# 데이터 초기화
signal_data = []
timestamps = []
peak_frequencies = []  # Peak frequencies for stability checks
last_peak_frequency = None
last_notification_sent = {'tense': False, 'calm': False, 'unstable': False}
instability_count = 0
instability_start_time = None

# 0.3 Hz ~ 0.7 Hz 범위의 극대값 주파수 추적용
low_freq_peak_frequency = None

def send_line_notify(notification_message):
    """
    LINE에 알림을 보내는 함수
    """
    line_notify_token = '7uKpqxcvSmjCsJo265uS9gW2Ox1m8zJimzipbUHDkqY'
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    data = {'message': notification_message}
    requests.post(line_notify_api, headers=headers, data=data)

# 실시간 데이터 업데이트 함수
def update(frame):
    global signal_data, timestamps, peak_frequencies, last_peak_frequency, last_notification_sent
    global instability_count, instability_start_time, low_freq_peak_frequency

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
                    N = 250
                      # 데이터 길이
                    signal_segment = signal_data[-N:]
                    
                    autocorr = np.correlate(signal_segment - np.mean(signal_segment), signal_segment - np.mean(signal_segment), mode='full')
                    autocorr = autocorr[len(autocorr) // 2:]  # 양의 시차 부분만 사용
                    
                    # 시차(lag) 값을 주파수(Hz)로 변환
                    T = 1.0 / 100.0  # 샘플링 주기 (초)
                    lags = np.arange(1, len(autocorr))  # 시차 0은 제외
                    frequencies = 1.0 / (lags * T)  # 주파수 = 1 / (시차 * 주기)

                    ax2.cla()
                    ax2.plot(frequencies, autocorr[1:])
                    ax2.set_title('Autocorrelation of ECG Signal (Frequency Domain)')
                    ax2.set_xlabel('Frequency (Hz)')
                    ax2.set_ylabel('Autocorrelation')
                    ax2.set_xlim(0, 2.5)  # X축 범위 설정
                    ax2.set_xticks(np.arange(0, 2.6, 0.1))  # X축 눈금을 0.1 단위로 설정

                    # 0.9 Hz ~ 2.1 Hz 범위에서의 극대치 찾기
                    mask_0_9_2_1 = (frequencies >= 0.9) & (frequencies <= 2.1)
                    selected_frequencies_0_9_2_1 = frequencies[mask_0_9_2_1]
                    selected_autocorr_0_9_2_1 = autocorr[1:][mask_0_9_2_1]

                    peak_indices_0_9_2_1 = np.argsort(selected_autocorr_0_9_2_1)[::-1]  # 내림차순으로 정렬
                    filtered_frequencies_0_9_2_1 = []
                    filtered_autocorr_0_9_2_1 = []

                    for idx in peak_indices_0_9_2_1:
                        frequency = selected_frequencies_0_9_2_1[idx]
                        autocorr_value = selected_autocorr_0_9_2_1[idx]
                        if not any(abs(frequency - f) < 0.5 * np.min(frequencies) for f in filtered_frequencies_0_9_2_1):
                            filtered_frequencies_0_9_2_1.append(frequency)
                            filtered_autocorr_0_9_2_1.append(autocorr_value)

                    if filtered_frequencies_0_9_2_1:
                        peak_frequency_1_2 = filtered_frequencies_0_9_2_1[0]
                        peak_value_1_2 = filtered_autocorr_0_9_2_1[0]
                        
                        # 상태 결정
                        if peak_frequency_1_2 >= 1.62:
                            current_state = 'tense'
                        else:
                            current_state = 'calm'

                        # 불안정성 판별
                        if last_peak_frequency is not None:
                            freq_change = abs(peak_frequency_1_2 - last_peak_frequency)
                            if freq_change > 0.1:
                                instability_count += 1
                                if instability_start_time is None:
                                    instability_start_time = time.time()
                                
                                elapsed_time = time.time() - instability_start_time
                                if elapsed_time <= 10 and instability_count >= 3:
                                    instability_state = 'unstable'
                                else:
                                    instability_state = 'stable'
                                    instability_count = 0
                                    instability_start_time = None
                            else:
                                instability_state = 'stable'
                                instability_count = 0
                                instability_start_time = None
                        else:
                            instability_state = 'stable'

                        # 상태에 따른 알림 전송
                        if current_state == 'tense' and not last_notification_sent['tense']:
                            send_line_notify('Seong-won’s heart rate appears to be elevated. \nIt might be helpful to contact Seong-won and suggest doing some deep breathing exercises together to relax.🧘‍♂️')
                            last_notification_sent['tense'] = True
                            last_notification_sent['calm'] = False
                        elif current_state == 'calm' and not last_notification_sent['calm']:
                            send_line_notify('It seems that Seong-won’s heart rate is lower than usual. \nHow about reaching out to Seong-won and suggesting a quiet, calming time together?💓')
                            last_notification_sent['calm'] = True
                            last_notification_sent['tense'] = False

                        if instability_state == 'unstable' and not last_notification_sent['unstable']:
                            send_line_notify('Seong-won’s heart rate seems unstable. In such situations,\n finding stability together can be beneficial. How about contacting Seong-won to explore calming methods together?💫')
                            last_notification_sent['unstable'] = True
                        elif instability_state == 'stable' and last_notification_sent['unstable']:
                            send_line_notify('Seong-won’s heart rate is returning to a stable state.\n To maintain this calm, consider reaching out to Seong-won and suggesting a walk or a quiet chat together.🌿')
                            last_notification_sent['unstable'] = False

                        # 마지막 극대값 갱신
                        last_peak_frequency = peak_frequency_1_2

                    # 0.0 Hz ~ 0.9 Hz 범위에서의 극대치 찾기
                    mask_0_0_0_9 = (frequencies >= 0.0) & (frequencies <= 0.9)
                    selected_frequencies_0_0_0_9 = frequencies[mask_0_0_0_9]
                    selected_autocorr_0_0_0_9 = autocorr[1:][mask_0_0_0_9]

                    peak_indices_0_0_0_9 = np.argsort(selected_autocorr_0_0_0_9)[::-1]  # 내림차순으로 정렬
                    filtered_frequencies_0_0_0_9 = []
                    filtered_autocorr_0_0_0_9 = []

                    for idx in peak_indices_0_0_0_9:
                        frequency = selected_frequencies_0_0_0_9[idx]
                        autocorr_value = selected_autocorr_0_0_0_9[idx]
                        if not any(abs(frequency - f) < 0.5 * np.min(frequencies) for f in filtered_frequencies_0_0_0_9):
                            filtered_frequencies_0_0_0_9.append(frequency)
                            filtered_autocorr_0_0_0_9.append(autocorr_value)

                    ax2.plot(filtered_frequencies_0_0_0_9, filtered_autocorr_0_0_0_9, 'ro', label='Breathing Peaks')
                    if filtered_frequencies_0_0_0_9:
                        low_freq_peak_frequency = filtered_frequencies_0_0_0_9[0]
                        peak_value_0_0_0_9 = filtered_autocorr_0_0_0_9[0]

                        print(f"Low frequency peak detected at {low_freq_peak_frequency:.2f} Hz with value {peak_value_0_0_0_9:.2f}")

            except ValueError:
                print(f"ValueError: Could not convert '{line}' to integer.")

# 그래프 설정
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# 애니메이션 설정
ani = FuncAnimation(fig, update, interval=100)
plt.tight_layout()
plt.show()

# 프로그램 종료 시 시리얼 포트 닫기
ser.close()
