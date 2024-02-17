from fastapi import FastAPI, WebSocket
import cv2
import numpy as np
import utlis
import easyocr
import re
from fastapi.middleware.cors import CORSMiddleware
import base64, os

app=FastAPI()
#allow cors
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],  
)

@app.websocket("/scan")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                id, address, dob, name=None, None, None, None
                b64_image = await websocket.receive_text()
                image_bytes = base64.b64decode(b64_image)
            
                text=warpAndScan(image_bytes)
                
                if "Address" in text or "A dd ress" in text or "Addre ss" in text or "Addrèss" in text or "Addres55" in text or "4ddress" in text or "Addrass" in text or "Add ress" in text or "Addre$$" in text or "sserdA" in text or "Addre5s" in text:
                    address=extractBack(text)
                else:
                    name, dob, id= extractFront(text)
            except:
                pass
            await websocket.send_json({"id":id,"dob":dob,"name":name, "address":address})
    except:
        print("connection died")
           
   



def warpAndScan(image):
    
    image_array = np.frombuffer(image, dtype=np.uint8)
    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    h=1600
    w=1200
    
    heightImg=800
    widthImg=600

    original_image=img

    img = cv2.resize(img, (widthImg, heightImg))  # RESIZE IMAGE
    original_image=cv2.resize(original_image, (w, h))
    

    imgBlank = np.zeros((heightImg, widthImg, 3), np.uint8)  # CREATE A BLANK IMAGE FOR TESTING DEBUGGING IF REQUIRED
    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # CONVERT IMAGE TO GRAY SCALE
    imgBlur = cv2.GaussianBlur(imgGray, (5,5), 1)  # ADD GAUSSIAN BLUR
    thres = utlis.valTrackbars()  # GET TRACK BAR VALUES FOR THRESHOLDS
    imgThreshold = cv2.Canny(imgBlur, thres[0], thres[1])  # APPLY CANNY BLUR
    kernel = np.ones((5, 5))
    imgDial = cv2.dilate(imgThreshold, kernel, iterations=2)  # APPLY DILATION
    imgThreshold = cv2.erode(imgDial, kernel, iterations=1)  # APPLY EROSION

    ## FIND ALL CONTOURS
    imgContours = img.copy()  # COPY IMAGE FOR DISPLAY PURPOSES
    imgBigContour = img.copy()  # COPY IMAGE FOR DISPLAY PURPOSES
    contours, hierarchy = cv2.findContours(imgThreshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # FIND ALL CONTOURS
    cv2.drawContours(imgContours, contours, -1, (0, 255, 0), 10)  # DRAW ALL DETECTED CONTOURS

    # FIND THE BIGGEST CONTOUR
    biggest, maxArea = utlis.biggestContour(contours)  # FIND THE BIGGEST CONTOUR
    # print(biggest.size)

    if biggest.size != 0:
        # print("entered if block")
        biggest_original=np.copy(biggest)
        # print(biggest_original[0][0][1])
        biggest_original[0][0][0]*=int(w/widthImg)
        biggest_original[0][0][1]*=int(w/widthImg)

        biggest_original[1][0][0]*=int(w/widthImg)
        biggest_original[1][0][1]*=int(w/widthImg)

        biggest_original[2][0][0]*=int(w/widthImg)
        biggest_original[2][0][1]*=int(w/widthImg)

        biggest_original[3][0][0]*=int(w/widthImg)
        biggest_original[3][0][1]*=int(w/widthImg)
        # print("biggest",biggest)
        # print(biggest.shape)

        # print("biggest original", biggest_original)
        
        biggest = utlis.reorder(biggest)
        biggest_original=utlis.reorder(biggest_original)
        
        
        cv2.drawContours(imgBigContour, biggest, -1, (0, 255, 0), 20)  # DRAW THE BIGGEST CONTOUR
        imgBigContour = utlis.drawRectangle(imgBigContour, biggest, 2)
        pts1 = np.float32(biggest)  # PREPARE POINTS FOR WARP
        pts1_original=np.float32(biggest_original)
        pts2 = np.float32([[0, 0], [widthImg, 0], [0, heightImg], [widthImg, heightImg]])  # PREPARE POINTS FOR WARP
        pts2_original=np.float32([[0, 0], [w, 0], [0, h], [w, h]]) 
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        matrix_original=cv2.getPerspectiveTransform(pts1_original, pts2_original)
        
        
        imgWarpColored = cv2.warpPerspective(img, matrix, (widthImg, heightImg),flags=cv2.INTER_CUBIC)
        imgWarpColored_original=cv2.warpPerspective(original_image, matrix_original, (w, h),flags=cv2.INTER_CUBIC)
        # # REMOVE 20 PIXELS FROM EACH SIDE
        # imgWarpColored = imgWarpColored[20:imgWarpColored.shape[0] - 20, 20:imgWarpColored.shape[1] - 20]
        # imgWarpColored = cv2.resize(imgWarpColored, (widthImg, heightImg))
        


        imgWarpColored_original=cv2.resize(imgWarpColored_original,(1300,840))

       
        reader = easyocr.Reader(['en','hi'])
        result = reader.readtext(imgWarpColored_original)
        text = ' '.join([entry[1] for entry in result])

    return text


     



def frontOrBack(text):
    if "Address" in text or "A dd ress" in text or "Addre ss" in text or "Addrèss" in text or "Addres55" in text or "4ddress" in text or "Addrass" in text or "Add ress" in text or "Addre$$" in text or "sserdA" in text or "Addre5s" in text:
        return "back"
    else:
        return "front"

def extractFront(text):
        # searching for keyword name ie a PAN card
        # searching for name in front 
        if text.find("Name") != -1:
            print("name found")
            name_pattern = r'\bName(?:\s*:\s*|\s+)(\w+\s+\w+)\b'
            name_match = re.search(name_pattern, text)
            name = name_match.group(1) if name_match else None
        # if keyword name not found in text
        # likely a aadhaar card
        if text.find("Name") == -1:
            # searching for name in front 
            start = text.find("DO8")
            if(start==-1):
                start = text.find("D08")
            if(start==-1):
                start = text.find("D08")
            if(start==-1):
                start = text.find("D0B")
            if(start==-1):
                start = text.find("DOB")



            print(start)
            name=""
            english="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            firstinstace=-1
            secondInstanceace=-1
            for i in range(start-1,-1,-1):

                if text[i] in english:
                    secondInstance=i
                    break
            for i in range(i-1,-1,-1):

                if text[i] not in english:
                    if(text[i].isspace()==False):
                        firstinstace=i+1
                        break
                

            name=text[firstinstace+1:secondInstance+1]
        # for dob

        dob_pattern = r"(\d{2}/\d{2}/\d{4})"
        dob_match = re.search(dob_pattern, text)
        dob = dob_match.group(1) if dob_match else None
        # dob searched

        # for id number
        aadhar_pattern = r"\b\d{4}\s?\d{4}\s?\d{4}\b"
        aadhar_match = re.search(aadhar_pattern, text)
    
        if aadhar_match is not None:
            id = aadhar_match.group() if aadhar_match else None
            return name,dob, id 
        if aadhar_match is None:
            desired_length = 10

            words = text.split()
            result_words = [word for word in words if len(word) == desired_length]
            
            for word in result_words:
                count_numbers = sum(char.isdigit() for char in word)
                if(count_numbers>=2 and count_numbers<=6):
                    id= word
                    return name, dob, id
def extractBack(extracted_text):
    # Extract text between "address" and a 12-digit number
    
    substring = "Address:"
    start = extracted_text.find(substring)
    if start is None:
        return "null"
    if(start==-1):
        start = extracted_text.find("Address")
    if(start==-1):
        start = extracted_text.find("address")
    if(start==-1):
        start = extracted_text.find("address:")
    
    start_index=start+len("Address:")
    

    aadhar_pattern = r"\b\d{4}\s?\d{4}\s?\d{4}\b"
    aadhar_match = re.search(aadhar_pattern, extracted_text)
    end_index = aadhar_match.start()

    return extracted_text[start_index:end_index]
    



    
# text=warpAndScan(image)
# id, address, dob, name= None, None, None, None
# frontOrBack = frontOrBack(text)
# if frontOrBack == "back":
#     address = extractBack(text)
    
# if frontOrBack == "front":
#     id, dob, name = extractFront(text)

# print(id, dob, name, address)
