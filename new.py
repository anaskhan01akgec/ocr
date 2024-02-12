from fastapi import FastAPI, WebSocket
import cv2,easyocr, re
from fastapi.middleware.cors import CORSMiddleware
import base64
import os
import numpy as np


app = FastAPI()
#allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],  
)

# WebSocket endpoint
@app.websocket("/scan")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:

            idtype,pan, name, dob, address = "null", "null", "null", "null", "null"
            
            

            base64_image = await websocket.receive_text()
            
            
            image_bytes = base64.b64decode(base64_image)



            #############################
            #real game here

            extracted_text = extract_text_from_image(image_bytes)
           # idtype=await findIdType(image_bytes)
            if any(variant in extracted_text for variant in ["Government Of India", "G0vernment 0f Ind1a", "Government 0f India", "Goverment 0f India", "Goverment Of India", "G0vernment Of Ind1a", "Government Of Ind1a", "Government Of India", "governm€nt 0f india", "government of india", "governm€nt 0f india"]):
                idtype="aadhaar"
            elif any(variant in extracted_text for variant in ["INCOME TAX DEPARTMENT", "INCOME T4X DEPARTMENT", "INCOME TAX DEP4RTMENT", "1NCOME TAX DEPARTMENT", "INCOME TAX DEP4RTMENT", "INCOME TAX DEPARTMENT", "INCOME TAX DEP4RTMENT", "INCOME TAX DEPARTMENT", "INCOME TAX DEPARTMENT", "INCOME TAX DEPARTMENT", "INCOME TAX DEPARTMENT"]):
                idtype="pan"
            
            if(idtype=="aadhaar"):
                # Extract name, DOB, and Aadhar number from the text
                dob, pan = extract_infoAadhaar(extracted_text)
        
                name = await nameSearchAadhaar(image_bytes)

            elif(idtype=="pan"):
                # Extract name, DOB, and Aadhar number from the text
                name, dob, pan = extract_infoPAN(extracted_text)
                if name==None:
                    name = await nameSearchPAN(image_bytes)

            

            ##################################
            
            
            if extracted_text=="":
                await websocket.send_text("no text in image")
	        
            if idtype is None:
                idtype = "null"
            
            elif re.search(r'\b\d{2}/\d{2}/\d{4}\b', extracted_text) is not None:
                
                await websocket.send_text(str({"name": name, "dob": dob, "document_number": pan, "document_type": idtype, "address": address}))
            else:

                address=extract_address(extracted_text)
                await websocket.send_text(str({"address": address}))
            
           
            
    except Exception as e:
        await websocket.send_text("internal server error")

#Function to extract address

def extract_address(extracted_text):
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

# Function to extract text from an image using EasyOCR
def extract_text_from_image(contents):
    reader = easyocr.Reader(['en'])
    result = reader.readtext(contents)
    text = ' '.join([entry[1] for entry in result])
    print("extracted text")
    return text

# Function to extract name, DOB, and Aadhar number from the extracted text
def extract_info(text):
    # Assuming simple patterns for name, DOB, and Aadhar number extraction
    name_pattern = r"Name: ([A-Za-z ]+)"
    dob_pattern = r"DOB : (\d{2}/\d{2}/\d{4})"
    aadhar_pattern = r"\b\d{4}\s?\d{4}\s?\d{4}\b"

    name_match = re.search(name_pattern, text)
    dob_match = re.search(dob_pattern, text)
    aadhar_match = re.search(aadhar_pattern, text)

    name = name_match.group(1) if name_match else None
    dob = dob_match.group(1) if dob_match else None
    aadhar = aadhar_match.group() if aadhar_match else None

    return name, dob, aadhar
def extract_infoAadhaar(text):
    # Assuming simple patterns for name, DOB, and Aadhar number extraction
    dob_pattern = r"DOB (\d{2}/\d{2}/\d{4})"
    aadhar_pattern = r"\b\d{4}\s?\d{4}\s?\d{4}\b"

    dob_match = re.search(dob_pattern, text)
    aadhar_match = re.search(aadhar_pattern, text)

    dob = dob_match.group(1) if dob_match else None
    aadhar = aadhar_match.group() if aadhar_match else None

    
    return dob, aadhar
def extract_infoPAN(text):
    # Assuming simple patterns for name, DOB, and Aadhar number extraction
    
    name_pattern = r'\bName(?:\s*:\s*|\s+)(\w+\s+\w+)\b'
    name_match = re.search(name_pattern, text)
    name = name_match.group(1) if name_match else None

    dob_pattern = r'\b\d{2}/\d{2}/\d{4}\b'
    pan_pattern = r"[A-Z]{5}[0-9]{4}[A-Z]{1}"


    dob_match = re.search(dob_pattern, text)
    pan_match= re.search(pan_pattern, text)

    dob = dob_match.group() if dob_match else None
    pan = pan_match.group() if pan_match else None
    
    
    return name,dob, pan
async def nameSearchAadhaar(contents):
    np_array = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    
    # Preprocessing
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    thresh = cv2.threshold(blur, 200, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 10))
    dilate = cv2.dilate(thresh, kernel, iterations=1)
    
    # Find contours
    cnts, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort contours by x-coordinate
    cnts = sorted(cnts, key=lambda x: cv2.boundingRect(x)[1])
    
    
    # Start of name search
    roi_counter=0

    name=""
    screen_height, screen_width = image.shape[:2]
   
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if (h / screen_height) * 100 >= 2 and (h / screen_height) * 100 <10 and (w / screen_width) * 100 >= 6:
            roi_counter=roi_counter+1
            roi = gray[y:y + h, x:x + w]
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            

            reader = easyocr.Reader(['en'])
            if roi_counter==4:
                name = reader.readtext(roi, detail=0, paragraph=False)[0]
                break
    
    # End of name search
    return name


async def nameSearchPAN(contents):
    np_array = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    
    # Preprocessing
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    thresh = cv2.threshold(blur, 200, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 10))
    dilate = cv2.dilate(thresh, kernel, iterations=1)
    
    # Find contours
    cnts, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort contours by x-coordinate
    cnts = sorted(cnts, key=lambda x: cv2.boundingRect(x)[1])
    
    
    # Start of name search
    roi_counter=0

    name=""
    screen_height, screen_width = image.shape[:2]
   
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if (h / screen_height) * 100 >= 2 and (h / screen_height) * 100 <10 and (w / screen_width) * 100 >= 6 and (y/screen_height)*100>23:
            roi = gray[y:y + h, x:x + w]
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            reader = easyocr.Reader(['en'])

            name = reader.readtext(roi, detail=0, paragraph=False)[0]
            break
    
    # End of name search
    return name




async def findIdType(contents):
    np_array = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    screen_height, screen_width = image.shape[:2]
    x1=int((216/736)*screen_width)
    x2=int((546/736)*screen_width)
    y1=int((50/490)*screen_height)
    y2=int((80/490)*screen_height)
    check_for_aadhaar=[x1,y1,x2,y2]
    reader = easyocr.Reader(['en'])
    cv2.imwrite("./forAadhar.jpg",image[y1:y2,x1:x2])
    result1 = reader.readtext(image[y1:y2,x1:x2])
    


    a1=int((30/1024)*screen_width)
    a2=int((450/1024)*screen_width)
    b1=int((100/654)*screen_height)
    b2=int((160/654)*screen_height)
    check_for_pan=[a1,b1,a2,b2]
    cv2.imwrite("./forPAN.jpg",image[b1:b2,a1:a2])

    result2 = reader.readtext(image[b1:b2,a1:a2])
    print("extracted id type")
    if(len(result1)!=0):
        if("Government of India" in result1[0] ):
            
            return "aadhaar"
    if(len(result2)!=0):
        if("INCOME TAX DEPARTMENT" in result2[0]):
            
            return "pan"
        
    
    



