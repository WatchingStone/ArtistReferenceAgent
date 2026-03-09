# 为了解决VisualEvaluator和LocalDB中chromadb的依赖库冲突问题，尝试将二者拆分成不同进程
import os
import multiprocessing
# 强制全局环境配置
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

from lib.dto.ImageInfoDTO import ImageInfoDTO

def consumer_local_db_treat_image_features(queue: multiprocessing.Queue):
    '''
    消费者进程（与主进程完全隔离），由local_db监听“跨进程队列multiprocessing.Queue”中传递的图片特征数据，然后处理
    :param queue:
    :return:
    '''
    print(">> [消费者进程]-[consumer_local_db_treat_image_features] 启动")
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1" # 强制该进程看不到 GPU
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"

    # 在子进程中导入LocalDB库，这样chromadb的dll只会在该进程中加载，不会和VisualEvaluator的torch冲突
    try:
        from lib.LocalDB import LocalDB
        db = LocalDB()
    except Exception as e:
        print(f">> [消费者进程] 初始化数据库失败: {e}")
        return

    # 开始监听队列
    while True:
        try:
            data = queue.get()  # 从队列中获取数据流

            # 约定data内容：如果收到data=None，则任务结束
            if data is None:
                print(">> [消费者进程]-[consumer_local_db_treat_image_features] 任务结束：接收到 data = None")
                break

            # 正常处理图片特征向量
            # image_dto, image_feature = data
            # db.add_image(image_dto, image_feature)
            image_dict, image_feature = data
            image_dto = ImageInfoDTO.from_dict(image_dict)
            db.add_image(image_dto, image_feature)
            print(">> [消费者进程]-[consumer_local_db_treat_image_features] 添加图片成功")
        except Exception as e:
            print(">> [消费者进程]-[consumer_local_db_treat_image_features] 添加失败：", str(e))

    print(">> [消费者进程]-[consumer_local_db_treat_image_features] 安全退出")

def producer_and_main_process(target_image_path: str):
    '''
    生产者进程（主进程），先启动消费者进程，然后再构造VisualEvaluator
    :param target_image_path: 检查的本地图片文件夹
    '''
    def _log(data: str):
        print(f">> [主进程]-[producer_and_main_process] {data}")

    _log(f"主进程启动，主进程ID为：{os.getpid()}")

    # 创建跨进程队列
    qmaxsize = 100
    queue = multiprocessing.Queue(maxsize=qmaxsize)  # 队列最大长度为100，防止内存被待处理的特征向量占满
    _log(f"创建跨进程队列，队列最大长度为：{qmaxsize}")

    # 启动消费者进程
    consumer_process = multiprocessing.Process(
        target=consumer_local_db_treat_image_features,
        args=(queue,)
    )
    consumer_process.start()
    _log(f"启动消费者进程，进程ID为：{consumer_process.pid}")

    # 启动主进程中的VisualEvaluator
    from lib.VisualEvaluator import VisualEvaluator
    from lib.LocalImageLoader import LocalImageLoader

    visual_evaluator = VisualEvaluator(config_path="D:/python/pythonProject/ArtistReferenceAgent/config/Resource_config.json")
    _log(f"初始化 VisualEvaluator() 完成")

    local_image_loader = LocalImageLoader()
    _log(f"初始化 LocalImageLoader() 完成")

    image_dtos = local_image_loader.scan_folder(target_image_path)
    image_features = local_image_loader.save_image_features(
        image_dtos=image_dtos,
        visual_evaluator=visual_evaluator,
        local_db=None
    )
    _log(f"提取图片特征向量完成，共 [{len(image_features)}] 张图片")

    del visual_evaluator

    # 将图片特征向量添加到队列中
    for image_dto, image_feature in zip(image_dtos, image_features):
        if not consumer_process.is_alive():
            _log("错误：检测到消费者进程已意外死亡！")
            break
        queue.put((image_dto.to_dict(), image_feature))

    queue.put(None)     # 添加结束标志

    # 等待消费者进程结束
    consumer_process.join()
    _log(f"消费者进程任务完成，所有进程结束")


if __name__ == '__main__':
    target_image_path = "E:/beiyong/test"
    producer_and_main_process(target_image_path)
