import tkinter as tk
from tkinter import ttk, Label, Text, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk, ImageChops
import sys, time, cv2, logging, subprocess, threading
import numpy as np
from pylinac import Starshot
import configparser
import os
from sklearn.linear_model import RANSACRegressor
from src.services import VideoStreamService

# 현재 스크립트 경로 가져오기
script_dir = os.path.dirname(os.path.abspath(__file__))

# 설정 파일 읽기 및 로그 설정
logging.basicConfig(
    filename='star_shot_analyzer.log',
    level=logging.INFO,
    filemode='w',
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%I:%M:%S'
)

config = configparser.ConfigParser()
config.read('config.ini')

# 설정값 읽기
ip_address_app = config.get('network', 'ip_address_app')
crop_x = int(config.get('crop', 'crop_x'))
crop_y = int(config.get('crop', 'crop_y'))
crop_w = int(config.get('crop', 'crop_w'))
crop_h = int(config.get('crop', 'crop_h'))

def ping_ip(ip_address):
    """IP 주소 연결 확인 함수"""
    try:
        # -c 1은 Linux/MacOS, -n 1은 Windows용으로 1번만 ping을 보냄
        result = subprocess.run(['ping', '-n', '1', ip_address], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE)
        if result.returncode == 0:
            logging.info(f"{ip_address} is reachable.")
            return True
        else:
            logging.info(f"{ip_address} is not reachable.")
            return False
    except Exception as e:
        logging.error(f"Ping error: {e}")
        return False

class VideoThread:
    """비디오 스트리밍 및 분석 처리 스레드 (Adapter for VideoStreamService with thread safety)

    This class wraps VideoStreamService and provides the same interface as the
    original VideoThread class for backward compatibility. All shared state is
    now protected by locks in the underlying VideoStreamService.
    """

    def __init__(self, callback=None):
        """Initialize VideoThread adapter.

        Args:
            callback: Optional callback function to invoke with each frame
        """
        # Create the underlying thread-safe video service
        # Apply cropping through a wrapper callback
        self._service = None
        self._callback = callback
        self._internal_thread = None
        self.cameraIsOn = False
        self.calThreadIsOn = False
        self.current_sum = 0
        self.max_sum = 0
        self.frame_with_max_sum = None
        self.cv_img = None

    def _on_frame_received(self, frame):
        """Internal callback that applies cropping and user callback.

        This runs in the video service thread and handles frame processing.

        Args:
            frame: OpenCV frame from video source
        """
        # Apply cropping
        cropped_frame = frame[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]

        # Store current frame
        self.cv_img = cropped_frame

        # Invoke user callback if provided
        if self._callback:
            try:
                self._callback(cropped_frame)
            except Exception as e:
                logging.error(f"Callback error: {e}")

    def start(self):
        """Start the video streaming thread (thread-safe)."""
        # Create video service with cropping callback
        self._service = VideoStreamService(
            video_source=f'http://{ip_address_app}:8000/stream.mjpg',
            callback=self._on_frame_received
        )

        # Start the service thread
        self._service.start()
        self.cameraIsOn = True

    def is_alive(self):
        """Check if video streaming thread is running."""
        if self._service is None:
            return False
        return self._service.is_alive()

    def stop(self):
        """Stop the video streaming thread gracefully (thread-safe)."""
        if self._service is not None:
            self._service.stop()
            self.cameraIsOn = False
        
class StarshotAnalyzer(tk.Tk):
    """Starshot 분석 메인 애플리케이션 클래스"""
    
    def __init__(self):
        super().__init__()
        self.title("Starshot Analyzer")
        self.geometry("1000x700")
        
        # 최소 크기 설정
        self.minsize(1000, 700)
        
        # 프레임 초기화
        self.init_ui()
        
        # 상태 변수 초기화
        self.thread = None
        self.laser_x = 0.0
        self.laser_y = 0.0
        self.dr_x = 0.0
        self.dr_y = 0.0
        self.img_merged = None
        self.create_empty_image()
        
        # 종료 시 리소스 해제 설정
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_empty_image(self):
        """빈 이미지 생성"""
        data = np.zeros([crop_h, crop_w, 3], dtype=np.uint8)
        self.img_merged = Image.fromarray(data, 'RGB')
    
    def init_ui(self):
        """UI 구성 초기화"""
        # 메뉴바 추가
        self.menu_bar = tk.Menu(self)
        
        # 파일 메뉴
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Connect", command=self.connect)
        file_menu.add_command(label="Edit Config", command=self.edit_config) 
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        
        # 도움말 메뉴
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=self.menu_bar)
        
        # 프레임 구성
        self.frame_control = ttk.LabelFrame(self, text="Control")
        self.frame_control.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.analyze_control = ttk.LabelFrame(self, text="Analyze")
        self.analyze_control.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # 이미지 프레임들을 가로로 배치
        self.frame_images = ttk.Frame(self)
        self.frame_images.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        self.frame_streaming = ttk.LabelFrame(self.frame_images, text="Streaming")
        self.frame_streaming.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.frame_starshot = ttk.LabelFrame(self.frame_images, text="Starshot")
        self.frame_starshot.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.frame_analyzed = ttk.LabelFrame(self.frame_images, text="Analyzed")
        self.frame_analyzed.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.frame_result = ttk.LabelFrame(self, text="Result")
        self.frame_result.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
       
        # 컨트롤 프레임 구성
        control_frame_left = ttk.Frame(self.frame_control)
        control_frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # self.btn_connect = ttk.Button(control_frame_left, text="Connect", command=self.connect)
        # self.btn_connect.pack(side=tk.LEFT, padx=5, pady=5)        
        
        self.btn_laser = ttk.Button(control_frame_left, 
                                    text="Capture\nLaser", command=lambda: self.capture_image("Laser"))
        self.btn_laser.pack(side=tk.LEFT, ipadx=0, ipady=0, padx=0, pady=3)
        
        self.btn_dr = ttk.Button(control_frame_left, 
                                 text="Capture\nDR", command=lambda: self.capture_image("DR"))
        self.btn_dr.pack(side=tk.LEFT, ipadx=0, ipady=0, padx=0, pady=3)
        
        self.btn_capture = ttk.Button(control_frame_left, 
                                      text="Capture\nStarline", command=self.toggle_capture)
        self.btn_capture.pack(side=tk.LEFT, ipadx=0, ipady=0, padx=0, pady=3)
        
        def adjust_dropdown_width():
            self.cmb_angle.configure(width=len(max(self.cmb_angle['values'], key=len)))

        self.cmb_angle = ttk.Combobox(control_frame_left, 
                                      values=["G000", "G030", "G090", "G150", "G240", "G300"], 
                                      width=4,  # 기본 너비 설정
                                      postcommand=adjust_dropdown_width)  # 드롭다운 시 너비 조절)
        self.cmb_angle.current(0)
        self.cmb_angle.pack(side=tk.LEFT, ipadx=0, ipady=0, padx=5, pady=5)
        
        # Analyze 프레임 구성
                
        # Analyze frame 구성
        # control_frame_right = ttk.Frame(self.frame_control)
        # control_frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.btn_merge = ttk.Button(self.analyze_control, text="1. Merge\n   Images", command=self.merge_images)
        self.btn_merge.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.btn_apply_laser = ttk.Button(self.analyze_control, text="2. Apply\n   Laser", command=self.apply_laser)
        self.btn_apply_laser.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.btn_apply_dr = ttk.Button(self.analyze_control, text="3. Apply\n   DR", command=self.apply_dr)
        self.btn_apply_dr.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.btn_analyze = ttk.Button(self.analyze_control, text="4. Analyze", command=self.analyze)
        self.btn_analyze.pack(side=tk.LEFT, padx=5, pady=5)
        
        # self.btn_close = ttk.Button(control_frame_right, text="Close", command=self.on_closing)
        # self.btn_close.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 스트리밍 프레임 구성
        self.lbl_stream = Label(self.frame_streaming)
        self.lbl_stream.pack(fill=tk.BOTH, expand=True)
        
        # Starshot 프레임 구성
        self.lbl_starshot = Label(self.frame_starshot)
        self.lbl_starshot.pack(fill=tk.BOTH, expand=True)
        
        # 결과 프레임 구성 - 결과 이미지는 이제 세 번째 이미지 프레임에 표시됨
        self.lbl_analyzed = Label(self.frame_analyzed)
        self.lbl_analyzed.pack(fill=tk.BOTH, expand=True)

        # 결과 프레임 구성 - grid 사용
        paned_window = tk.PanedWindow(self.frame_result, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        result_frame_left = ttk.Frame(paned_window)
        result_frame_right = ttk.Frame(paned_window)
        
        paned_window.add(result_frame_left)
        paned_window.add(result_frame_right)        

        # # 초기 위치 설정 (픽셀 단위)
        # paned_window.sash_place(0, 100, 0)  # 첫 번째 구분자를 x=300 위치에 배치

        # result_frame_left = ttk.Frame(self.frame_result)
        # result_frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # result_frame_right = ttk.Frame(self.frame_result)
        # result_frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 로그 텍스트 영역
        self.txt_log = ScrolledText(result_frame_right, height=6)
        self.txt_log.pack(fill=tk.BOTH, expand=True)
        
        # 결과 테이블
        columns = ('min_radius', 'vs_laser', 'vs_dr')
        self.tbl_result = ttk.Treeview(result_frame_left, columns=columns, show='headings', height=1)
        
        self.tbl_result.heading('min_radius', text='Min. Radius')
        self.tbl_result.heading('vs_laser', text='vs Laser')
        self.tbl_result.heading('vs_dr', text='vs DR')
        
        self.tbl_result.column('min_radius', width=300)
        self.tbl_result.column('vs_laser', width=200)
        self.tbl_result.column('vs_dr', width=200)
        
        self.tbl_result.pack(fill=tk.BOTH, expand=True)
        
        
        # 그리드 가중치 설정 - 이미지 프레임에 더 많은 공간 할당
        self.grid_rowconfigure(0, weight=1)    # 컨트롤 영역 (작게)
        self.grid_rowconfigure(1, weight=5)    # 이미지 영역 (크게)
        self.grid_rowconfigure(2, weight=1)    # 결과 영역 (작게)        
        self.grid_columnconfigure(0, weight=1)        
    
    def update_stream_image(self, cv_img):
        """스트리밍 이미지 업데이트"""
        if cv_img is not None:
            # OpenCV BGR -> RGB 변환
            rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            # PIL 이미지로 변환
            pil_img = Image.fromarray(rgb_img)
            # 화면 크기에 맞게 리사이즈
            pil_img = self.resize_image(pil_img, self.frame_streaming.winfo_width(), 
                                       self.frame_streaming.winfo_height())
            # Tkinter PhotoImage로 변환
            img_tk = ImageTk.PhotoImage(image=pil_img)
            
            # 라벨에 이미지 표시
            self.lbl_stream.img_tk = img_tk  # 참조 유지
            self.lbl_stream.config(image=img_tk)
    
    def update_starshot_image(self, pil_img=None, cv_img=None):
        """Starshot 이미지 업데이트"""
        if pil_img is None and cv_img is not None:
            # OpenCV 이미지가 제공된 경우
            rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)
        
        if pil_img is not None:
            # 화면 크기에 맞게 리사이즈
            pil_img = self.resize_image(pil_img, self.frame_starshot.winfo_width(), 
                                       self.frame_starshot.winfo_height())
            # Tkinter PhotoImage로 변환
            img_tk = ImageTk.PhotoImage(image=pil_img)
            
            # 라벨에 이미지 표시
            self.lbl_starshot.img_tk = img_tk  # 참조 유지
            self.lbl_starshot.config(image=img_tk)
    
    def update_analyzed_image(self, pil_img=None, cv_img=None):
        """분석 결과 이미지 업데이트"""
        if pil_img is None and cv_img is not None:
            # OpenCV 이미지가 제공된 경우
            rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)
        
        if pil_img is not None:
            # 화면 크기에 맞게 리사이즈
            pil_img = self.resize_image(pil_img, self.frame_analyzed.winfo_width(), 
                                       self.frame_analyzed.winfo_height())
            # Tkinter PhotoImage로 변환
            img_tk = ImageTk.PhotoImage(image=pil_img)
            
            # 라벨에 이미지 표시
            self.lbl_analyzed.img_tk = img_tk  # 참조 유지
            self.lbl_analyzed.config(image=img_tk)
    
    def resize_image(self, img, width, height):
        """이미지를 지정된 크기에 맞게 비율 유지하며 리사이즈"""
        if width <= 1 or height <= 1:  # 윈도우 크기가 아직 결정되지 않은 경우
            return img
            
        img_width, img_height = img.size
        ratio = min(width/img_width, height/img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        return img.resize((new_width, new_height), Image.LANCZOS)
    
    def connect(self):
        """카메라 연결 함수"""
        try:
            if self.thread is not None and self.thread.is_alive():
                self.log_message("이미 연결되어 있습니다.")
                return
                
            if ping_ip(ip_address_app):
                # 스레드 생성 및 시작
                self.thread = VideoThread(callback=self.update_stream_image)
                self.thread.daemon = True  # 메인 스레드 종료 시 같이 종료
                self.thread.start()
                
                self.log_message(f"IP 주소에 연결됨: {ip_address_app}")
            else:
                self.log_message(f"오류: 연결할 수 없음! ({ip_address_app})")
        except Exception as e:
            self.log_message(f"연결 오류: {str(e)}")
            logging.error(f"Connection error: {str(e)}")
    
    def toggle_capture(self):
        """Starline 캡처 토글 함수 (thread-safe)"""
        if self.thread is None or not self.thread.is_alive():
            self.log_message("카메라가 연결되지 않았습니다. 먼저 'Connect'를 클릭하세요.")
            return

        if not self.thread.calThreadIsOn:
            # 측정 시작 (버튼 텍스트 = 'Get starline')
            gantry_angle = self.cmb_angle.get()
            logging.info(f"{gantry_angle}: 측정 시작.")
            self.btn_capture.config(text="Stop")
            self.log_message("실시간 스트리밍 데이터 기록 중...")

            # Enable calculation mode in underlying service (thread-safe)
            self.thread.calThreadIsOn = True
            self.thread._service.enable_calculation()
            self.thread._service.reset_calculation()
        else:
            # 측정 중 (버튼 텍스트 = 'Stop')
            tsec = time.time()
            gantry_angle = self.cmb_angle.get()
            filename = time.strftime("%Y%m%d", time.localtime(tsec)) + "_Starline_" + gantry_angle

            # Disable calculation mode in underlying service (thread-safe)
            self.thread.calThreadIsOn = False
            self.thread._service.disable_calculation()

            self.btn_capture.config(text="Capture Starline")

            # Get brightest frame (thread-safe)
            brightest_frame = self.thread._service.get_brightest_frame()
            if brightest_frame is not None:
                img = Image.fromarray(brightest_frame)

                default_file_name = filename + ".jpg"
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".jpg",
                    initialfile=default_file_name,
                    filetypes=[("JPEG files", "*.jpg")]
                )

                if file_path:
                    img.save(file_path)
                    self.log_message(f"스틸샷 추출 완료: {filename[0:13]}")
                    logging.info(f"{gantry_angle}: 획득 완료.")
    
    def capture_image(self, image_type):
        """이미지 캡처 통합 함수 (thread-safe)"""
        if self.thread is None or not self.thread.is_alive():
            self.log_message("카메라가 연결되지 않았습니다. 먼저 'Connect'를 클릭하세요.")
            return

        try:
            # Get current frame safely through thread-safe accessor
            current_frame = self.thread._service.get_current_frame()
            if current_frame is None:
                self.log_message("현재 프레임을 가져올 수 없습니다.")
                return

            tsec = time.time()
            tname = time.strftime("%Y%m%d-%H%M%S", time.localtime(tsec))

            fname = tname + f"_{image_type}.jpg"
            cv2.imwrite(fname, current_frame)

            self.log_message(f"  ---   {image_type} 이미지 캡처 완료   ---")
            logging.info(f"  ---   {image_type} 이미지 캡처 완료   ---")
        except Exception as e:
            self.log_message(f"이미지 캡처 오류: {str(e)}")
            logging.error(f"Image capture error: {str(e)}")
    
    def merge_images(self):
        """이미지 합성 함수"""
        try:
            file_paths = filedialog.askopenfilenames(
                title="Select Files",
                filetypes=[("JPEG files", "*.jpg")],
                initialdir=script_dir
            )
            
            if not file_paths:
                return
                
            merged_starshot = None
            for file_path in file_paths:
                with Image.open(file_path) as image:
                    if merged_starshot is None:
                        merged_starshot = image.copy()  # 첫 번째 이미지 복사
                    else:
                        merged_starshot = ImageChops.add(merged_starshot, image)  # 이미지 합성
            
            if merged_starshot is not None:
                self.img_merged = merged_starshot.copy()
                self.update_starshot_image(pil_img=self.img_merged)
                
                # 결과 저장
                tsec = time.time()
                tname = time.strftime("%Y%m%d", time.localtime(tsec))
                merge_filename = tname + "_starshot(merged).jpg"
                merge_filepath = filedialog.asksaveasfilename(
                    defaultextension=".jpg",
                    initialfile=merge_filename,
                    filetypes=[("JPEG files", "*.jpg")]
                )
                
                if merge_filepath:
                    self.img_merged.save(merge_filepath)
                
                self.log_message("Starshot(합성) 이미지 획득 완료.")
                logging.info("  ---   Starshot(합성) 이미지 획득 완료   ---")
        except Exception as e:
            self.log_message(f"이미지 합성 오류: {str(e)}")
            logging.error(f"Image merging error: {str(e)}")
    
    def apply_laser(self):
        """레이저 등중심점 적용 함수"""
        try:
            file_path = filedialog.askopenfilename(
                title="Select a laser isocenter image",
                filetypes=[("JPEG files", "*.jpg")], initialdir=script_dir
            )
            
            if not file_path:
                return
            
            with Image.open(file_path) as laser_img_rgb:
                laser_img = laser_img_rgb.convert("L")
                crop_laser_image = np.array(laser_img)
                
            h, w = crop_laser_image.shape
            
            roi_size = 200
            crop_roi = crop_laser_image[int(h/2)-roi_size:int(h/2)+roi_size, 
                                        int(w/2)-roi_size:int(w/2)+roi_size]
            blurred = cv2.GaussianBlur(crop_roi, (5, 5), 0)  # 블러 처리
            
            # 임계값 처리
            _, tmp_thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            thresh = ~tmp_thresh
            
            N_iter = 10
            size_v, size_h = crop_roi.shape
            pos_vert = []
            pos_horz = []
            xy_pos = np.zeros(N_iter-1)
            
            for i in range(N_iter - 1):
                idx = int((size_v/N_iter)*(i+1))
                line_vert = thresh[:,idx]
                line_horz = thresh[idx,:]
                
                xy_pos[i] = idx
                
                pos_vert.append(np.mean(np.where(line_vert < 10)[0]))
                pos_horz.append(np.mean(np.where(line_horz < 10)[0]))
            
            pos_vert = np.array(pos_vert)
            pos_horz = np.array(pos_horz)
            
            # 수평선 분석
            ransac = RANSACRegressor(residual_threshold=2)
            hor_x = xy_pos.reshape(-1, 1)
            hor_y = pos_horz
            ransac.fit(hor_x, hor_y)
            
            hor_slope = ransac.estimator_.coef_[0]
            hor_intercept = ransac.estimator_.intercept_
            
            # 수직선 분석
            ransac = RANSACRegressor(residual_threshold=2)
            ver_x = xy_pos.reshape(-1, 1)
            ver_y = pos_vert
            ransac.fit(ver_x, ver_y)
            
            ver_slope = ransac.estimator_.coef_[0]
            ver_intercept = ransac.estimator_.intercept_
            
            # 레이저 중심점 계산
            if (abs(ver_slope) > 1/100):
                ori_ver_slope = -1 / ver_slope
                ori_ver_intercept = -hor_intercept / ver_slope
                determinant = -hor_slope + ori_ver_slope
                self.laser_x = int(w/2)-roi_size+(-ori_ver_intercept + hor_intercept)/determinant
                self.laser_y = int(h/2)-roi_size+(hor_intercept*ori_ver_slope - ori_ver_intercept*hor_slope)/determinant
            else:
                self.laser_x = int(w/2)-roi_size+hor_intercept
                self.laser_y = int(h/2)-roi_size+ver_intercept
            
            # 레이저 중심점 표시
            b_sz = 4
            tmp_laser_center_image = np.zeros([h, w, 3], dtype=np.uint8)
            tmp_laser_center_image[int(self.laser_y)-b_sz:int(self.laser_y)+b_sz, 
                                  int(self.laser_x)-b_sz:int(self.laser_x)+b_sz, 0] = 255
            laser_center_image = Image.fromarray(tmp_laser_center_image, 'RGB')
            
            if self.img_merged is not None:
                self.img_merged = ImageChops.add(self.img_merged, laser_center_image)
                self.update_starshot_image(pil_img=self.img_merged)
            
            self.log_message(f"레이저 등중심점: ({round(self.laser_x, 0)}, {round(self.laser_y, 0)})")
            self.log_message("레이저 등중심점 적용이 완료되었습니다.")
            logging.info("  ---   레이저 등중심점 적용이 완료되었습니다.   ---")
        except Exception as e:
            self.log_message(f"레이저 적용 오류: {str(e)}")
            logging.error(f"Laser application error: {str(e)}")
    
    def apply_dr(self):
        """DR 중심점 적용 함수"""
        try:
            file_path = filedialog.askopenfilename(
                title="Select a DR center image",
                filetypes=[("JPEG files", "*.jpg")], initialdir=script_dir
            )
            
            if not file_path:
                return
            
            with Image.open(file_path) as dr_img_rgb:
                dr_img = dr_img_rgb.convert("L")
                w, h = dr_img.size
                crop_dr_img = np.array(dr_img)
            
            roi_size = 200
            crop_roi = crop_dr_img[int(h/2)-roi_size:int(h/2)+roi_size, 
                                  int(w/2)-roi_size:int(w/2)+roi_size]
            
            blurred = cv2.GaussianBlur(crop_roi, (5, 5), 0)  # 블러 처리
            # Threshold the image to create a binary image with OTSU algorithm
            _, tmp_thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            thresh = ~tmp_thresh  # 임계값 이미지 반전
            
            # 바이너리 이미지에서 윤곽선 찾기
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            min_area = 10  # 최소 면적 (픽셀 단위)
            max_area = 500  # 최대 면적 (픽셀 단위)
            filtered_contours = [cnt for cnt in contours if min_area < cv2.contourArea(cnt) < max_area]
            
            if filtered_contours:  # 필터링된 윤곽선이 존재하는 경우
                # 가장 큰 윤곽선 찾기
                largest_contour = max(filtered_contours, key=cv2.contourArea)
                
                M = cv2.moments(largest_contour)
                if M["m00"] != 0:
                    self.dr_x = int(w/2) - roi_size + int(M["m10"] / M["m00"])
                    self.dr_y = int(h/2) - roi_size + int(M["m01"] / M["m00"])
                    
                    # DR 중심점 표시
                    b_sz = 4
                    tmp_dr_center_image = np.zeros([h, w, 3], dtype=np.uint8)
                    tmp_dr_center_image[self.dr_y-b_sz:self.dr_y+b_sz, 
                                        self.dr_x-b_sz:self.dr_x+b_sz, 0] = 255
                    dr_center_image = Image.fromarray(tmp_dr_center_image, 'RGB')
                    
                    if self.img_merged is not None:
                        self.img_merged = ImageChops.add(self.img_merged, dr_center_image)
                        self.update_starshot_image(pil_img=self.img_merged)
                    
                    self.log_message(f"DR 중심점: ({round(self.dr_x, 0)}, {round(self.dr_y, 0)})")
                    self.log_message("DR 중심점 적용이 완료되었습니다.")
                    logging.info("  ---   DR 중심점 적용이 완료되었습니다.   ---")
            else:
                self.log_message("DR 중심점을 찾지 못했습니다.")
        except Exception as e:
            self.log_message(f"DR 적용 오류: {str(e)}")
            logging.error(f"DR application error: {str(e)}")
    
    def analyze(self):
        """Starshot 분석 수행 함수"""
        try:
            if self.img_merged is None:
                self.log_message("분석할 Starshot 이미지가 없습니다. 먼저 이미지를 합성하세요.")
                return
                
            # 픽셀당 mm 비율 설정
            dpmm_meas = 231.5 / 30
            dpi_mea = dpmm_meas * 25.4
            
            # 임시 파일로 이미지 저장 후 pylinac으로 분석
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                self.img_merged.save(tmp_file.name)
                tmp_file_name = tmp_file.name
            
            # Starshot 분석
            mystar = Starshot(tmp_file_name, dpi=dpi_mea, sid=1000)
            mystar.analyze()
            
            # 결과 데이터 추출
            result_data = mystar.results_data()
            passed = result_data.passed
            diameter = result_data.circle_diameter_mm
            star_x = result_data.circle_center_x_y[0]
            star_y = result_data.circle_center_x_y[1]
            
            # 레이저 및 DR 중심점과의 차이 계산
            result1 = (self.laser_x - star_x) / dpmm_meas
            result2 = (self.laser_y - star_y) / dpmm_meas
            result3 = (self.dr_x - star_x) / dpmm_meas
            result4 = (self.dr_y - star_y) / dpmm_meas
            
            # 결과 로그 출력
            self.log_message(
                f"레이저 등중심점: ({round(self.laser_x, 2)}, {round(self.laser_y, 2)})\n"
                f"DR 중심점: ({round(self.dr_x, 2)}, {round(self.dr_y, 2)})\n"
                f"방사선 등중심점: ({round(star_x, 2)}, {round(star_y, 2)})"
            )
            
            self.log_message(
                f"검사 결과: {passed} / 최소 원 반경: {round(diameter, 3)} mm.\n"
                "방사선 등중심점과의 위치 차이:\n"
                f"레이저 vs. 방사선: ({round(result1, 2)}, {round(result2, 2)}) mm.\n"
                f"DR vs. 방사선: ({round(result3, 2)}, {round(result4, 2)}) mm."
            )
            
            # 결과 테이블 업데이트
            self.tbl_result.delete(*self.tbl_result.get_children())
            self.tbl_result.insert('', 'end', values=(
                f"{round(diameter, 1)} mm",
                f"({round(result1, 1)}, {round(result2, 1)}) mm",
                f"({round(result3, 1)}, {round(result4, 1)}) mm"
            ))
            
            # 결과 이미지 저장 및 표시
            tsec = time.time()
            tname = time.strftime("%Y%m%d", time.localtime(tsec))
            result_filename = tname + "_Result"
            
            # 분석 이미지 저장
            mystar.save_analyzed_subimage(result_filename, True)
            result_filename_open = result_filename + '.png'
            
            # 결과 이미지 표시
            with Image.open(result_filename_open) as starshot_img:
                self.update_analyzed_image(pil_img=starshot_img)
            
            self.log_message("Starshot 분석이 완료되었습니다.")
            logging.info("  ---   Starshot 분석이 완료되었습니다.   ---")
            
            # 임시 파일 삭제
            os.unlink(tmp_file_name)
        except Exception as e:
            self.log_message(f"분석 오류: {str(e)}")
            logging.error(f"Analysis error: {str(e)}")
    
    def log_message(self, message):
        """로그 메시지 추가 함수"""
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)  # 스크롤을 최신 메시지로 이동        
        
    def edit_config(self):
        """INI 파일 편집 윈도우"""
        config_window = tk.Toplevel(self)
        config_window.title("설정 편집")
        config_window.geometry("400x400")
        config_window.resizable(False, False)
        config_window.grab_set()  # 모달 윈도우로 설정
        
        # 현재 설정 불러오기
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # 네트워크 설정 프레임
        net_frame = ttk.LabelFrame(config_window, text="네트워크 설정")
        net_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(net_frame, text="IP 주소:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ip_var = tk.StringVar(value=config.get('network', 'ip_address_app'))
        ip_entry = ttk.Entry(net_frame, textvariable=ip_var, width=15)
        ip_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 크롭 설정 프레임
        crop_frame = ttk.LabelFrame(config_window, text="이미지 크롭 설정")
        crop_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(crop_frame, text="X:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        crop_x_var = tk.IntVar(value=int(config.get('crop', 'crop_x')))
        crop_x_entry = ttk.Entry(crop_frame, textvariable=crop_x_var, width=5)
        crop_x_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(crop_frame, text="Y:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        crop_y_var = tk.IntVar(value=int(config.get('crop', 'crop_y')))
        crop_y_entry = ttk.Entry(crop_frame, textvariable=crop_y_var, width=5)
        crop_y_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(crop_frame, text="너비:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        crop_w_var = tk.IntVar(value=int(config.get('crop', 'crop_w')))
        crop_w_entry = ttk.Entry(crop_frame, textvariable=crop_w_var, width=5)
        crop_w_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(crop_frame, text="높이:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        crop_h_var = tk.IntVar(value=int(config.get('crop', 'crop_h')))
        crop_h_entry = ttk.Entry(crop_frame, textvariable=crop_h_var, width=5)
        crop_h_entry.grid(row=1, column=3, padx=5, pady=5)
        
        # 버튼 프레임
        btn_frame = ttk.Frame(config_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_config():
            try:
                # 설정값 검증
                try:
                    crop_x_val = int(crop_x_var.get())
                    crop_y_val = int(crop_y_var.get())
                    crop_w_val = int(crop_w_var.get())
                    crop_h_val = int(crop_h_var.get())
                    
                    if crop_w_val <= 0 or crop_h_val <= 0:
                        raise ValueError("너비와 높이는 양수여야 합니다.")
                except ValueError as e:
                    messagebox.showerror("입력 오류", f"잘못된 입력: {str(e)}")
                    return
                
                # 설정 업데이트
                config.set('network', 'ip_address_app', ip_var.get())
                config.set('crop', 'crop_x', str(crop_x_val))
                config.set('crop', 'crop_y', str(crop_y_val))
                config.set('crop', 'crop_w', str(crop_w_val))
                config.set('crop', 'crop_h', str(crop_h_val))
                
                # 파일에 저장
                with open('config.ini', 'w') as configfile:
                    config.write(configfile)
                
                # 전역 변수 업데이트
                global ip_address_app, crop_x, crop_y, crop_w, crop_h
                ip_address_app = ip_var.get()
                crop_x = crop_x_val
                crop_y = crop_y_val
                crop_w = crop_w_val
                crop_h = crop_h_val
                
                self.log_message("설정이 저장되고 적용되었습니다.")
                messagebox.showinfo("설정 업데이트", f"설정 파일을 업데이트했습니다.\nIP: {ip_address_app}\n크롭: ({crop_x}, {crop_y}, {crop_w}, {crop_h})")
                config_window.destroy()
            except Exception as e:
                messagebox.showerror("오류", f"설정 저장 오류: {str(e)}")
        
        # 버튼을 내용에 맞게 배치
        ttk.Button(btn_frame, text="저장&적용", command=save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="취소", command=config_window.destroy).pack(side=tk.LEFT, padx=5)

    
    def reload_config(self):
        """설정 파일 다시 읽기"""
        try:
            global ip_address_app, crop_x, crop_y, crop_w, crop_h
            
            config = configparser.ConfigParser()
            config.read('config.ini')
            
            # 설정값 업데이트
            ip_address_app = config.get('network', 'ip_address_app')
            crop_x = int(config.get('crop', 'crop_x'))
            crop_y = int(config.get('crop', 'crop_y'))
            crop_w = int(config.get('crop', 'crop_w'))
            crop_h = int(config.get('crop', 'crop_h'))
            
            self.log_message("설정 파일을 다시 읽었습니다.")
            messagebox.showinfo("설정 다시 읽기", f"설정 파일을 다시 읽었습니다.\nIP: {ip_address_app}\n크롭: ({crop_x}, {crop_y}, {crop_w}, {crop_h})")
        except Exception as e:
            self.log_message(f"설정 파일 읽기 오류: {str(e)}")
            messagebox.showerror("오류", f"설정 파일 읽기 오류: {str(e)}")

    def show_about(self):
        """프로그램 정보 표시"""
        about_text = """
        Starshot Analyzer v3.0
            
        방사선 치료기 등중심점 품질관리 도구
        의학물리 QA 분석용 소프트웨어
        
        이 프로그램은 Pylinac 라이브러리를 활용합니다.
        
        2025. 3. - Kwanghyun Jo
        """
        messagebox.showinfo("프로그램 정보", about_text)
    
    def on_closing(self):
        """프로그램 종료 시 처리 함수"""
        if messagebox.askokcancel("종료", "프로그램을 종료하시겠습니까?"):
            # 리소스 정리
            if self.thread is not None:
                self.thread.stop()
                
            logging.shutdown()
            self.destroy()

if __name__ == "__main__":
    # 필요한 추가 임포트
    import os
    import tempfile
    
    app = StarshotAnalyzer()
    app.mainloop()