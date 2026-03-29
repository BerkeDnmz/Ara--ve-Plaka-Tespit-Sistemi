# importing required libraries
import cv2
import mysql.connector
import numpy as np
 
dataBase = mysql.connector.connect(
  host ="localhost",                # Localhost for local connection
  user ="root",
  passwd ="password",
  database ="db_car"
)

 

def addRecord(plate, image, color, video_path, input_sql): #Adds records to database. Both into records and videos databases.
    try:
        dataBase = mysql.connector.connect(
          host = input_sql["host"],                # Localhost for local connection
          user = input_sql["user"],
          passwd = input_sql["password"],
          database = input_sql["database"]
        )
        img_str = cv2.imencode('.jpg', image)[1].tobytes()
        sql = "INSERT INTO records (plate, image, color)\
    VALUES (%s, %s, %s)"
        val = (plate, img_str, color)
        cursor = dataBase.cursor()
        cursor.execute(sql, val)
        dataBase.commit()
        
        sql = "INSERT INTO videos (video_path, record_id)\
    VALUES (%s, %s)"
        val = (video_path, cursor.lastrowid)
        cursor.execute(sql, val)
        dataBase.commit()
        dataBase.close()
    except mysql.connector.Error as error:
        print(format(error))
    finally:
        if dataBase.is_connected():
            cursor.close()
            dataBase.close()
            print("addRecord")
            
def updateRecord(car_id, plate, color):
    try:
        dataBase = mysql.connector.connect(
          host ="localhost",                # Localhost for local connection
          user ="root",
          passwd ="password",
          database ="db_car"
        )
        sql = "UPDATE records SET plate = %s, color = %s WHERE id = %s"
        val = (plate, color, car_id)
        cursor = dataBase.cursor()
        cursor.execute(sql, val)
        dataBase.commit()
        dataBase.close()
    except mysql.connector.Error as error:
        print(format(error))
    finally:
        if dataBase.is_connected():
            cursor.close()
            dataBase.close()
            print("updateRecord")
            
def deleteRecord(car_id):
    try:
        dataBase = mysql.connector.connect(
          host ="localhost",                # Localhost for local connection
          user ="root",
          passwd ="password",
          database ="db_car"
        )
        sql = "DELETE FROM videos WHERE record_id = %s"
        val = (car_id)
        cursor = dataBase.cursor()
        cursor.execute(sql, val)
        dataBase.commit()
        
        sql = "DELETE FROM records WHERE id = %s"
        val = (car_id)
        cursor = dataBase.cursor()
        cursor.execute(sql, val)
        dataBase.commit()
        
        dataBase.close()
    except mysql.connector.Error as error:
        print(format(error))
    finally:
        if dataBase.is_connected():
            cursor.close()
            dataBase.close()
            print("deleteRecord")
    
def checkRecord(plate, input_sql): #Checks if the record is added before and doesn't if so
    try:
        dataBase = mysql.connector.connect(
          host = input_sql["host"],                # Localhost for local connection
          user = input_sql["user"],
          passwd = input_sql["password"],
          database = input_sql["database"]
        )
        cursor = dataBase.cursor()
        cursor.execute(
            "SELECT * FROM records WHERE plate = %s",
            (plate,))
        row_count = cursor.rowcount
        myresult = cursor.fetchall() #Unneeded but dataBase gives unread result error without it.
        if(row_count == 0):
            return True
        else:
            return False
        
        dataBase.close()
    except mysql.connector.Error as error:
        print(format(error))
    finally:
        if dataBase.is_connected():
            cursor.close()
            dataBase.close()
            print("checkRecord")
            
def getRecords(): #Gets the records list
    try:
        dataBase = mysql.connector.connect(
          host ="localhost",                # Localhost for local connection
          user ="root",
          passwd ="password",
          database ="db_car"
        )
        cursor = dataBase.cursor()
        cursor.execute("SELECT videos.record_id, records.plate, records.image, records.color, videos.video_path FROM videos INNER JOIN records WHERE records.id = videos.record_id")
        
        result = cursor.fetchall()
        return result
        
        dataBase.close()
    except mysql.connector.Error as error:
        print(format(error))
    finally:
        if dataBase.is_connected():
            cursor.close()
            dataBase.close()
            print("checkRecord")
            
def getImage(plate): #Gets the image of the record
    try:
        dataBase = mysql.connector.connect(
          host ="localhost",                # Localhost for local connection
          user ="root",
          passwd ="password",
          database ="db_car"
        )
        cursor = dataBase.cursor()
        cursor.execute(
            "SELECT image FROM records WHERE plate = %s",
            (plate,))
        
        result = cursor.fetchone()
        #print(type(result))
        #result = np.float32(result)
        #result = np.frombuffer(result, np.uint8)
        result = np.frombuffer(result[0], np.uint8)
        image = cv2.imdecode(result, cv2.IMREAD_COLOR)
        
        return image
        
        dataBase.close()
    except mysql.connector.Error as error:
        print(format(error))
    finally:
        if dataBase.is_connected():
            cursor.close()
            dataBase.close()
            print("checkRecord")
            
def checkTable(input_sql): #Checks if table needed exists
    try:
        dataBase = mysql.connector.connect(
          host = input_sql["host"],                # Localhost for local connection
          user = input_sql["user"],
          passwd = input_sql["password"],
          database = input_sql["database"]
        )
        sql = "SHOW TABLES"
        table1 = "records"
        table2 = "videos"
        cursor = dataBase.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        
        result_list = [item[0] for item in result]
        
        if table1 in result_list and table2 in result_list:
            return True
        else:
            return False
        
        dataBase.close()
    except mysql.connector.Error as error:
        print(format(error))
    finally:
        if dataBase.is_connected():
            cursor.close()
            dataBase.close()
            print("checkTable")

def createTable(input_sql): #Creates the tables needed
    try:
        dataBase = mysql.connector.connect(
          host = input_sql["host"],                # Localhost for local connection
          user = input_sql["user"],
          passwd = input_sql["password"],
          database = input_sql["database"]
        )
        sql = """CREATE TABLE `records` (
   `id` int NOT NULL AUTO_INCREMENT,
   `plate` varchar(45) NOT NULL DEFAULT '????',
   `image` longblob,
   `color` varchar(45) NOT NULL DEFAULT '????',
   PRIMARY KEY (`id`)
 ) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
        cursor = dataBase.cursor()
        cursor.execute(sql)
        dataBase.commit()
        
        sql = """CREATE TABLE `videos` (
   `id` int NOT NULL AUTO_INCREMENT,
   `video_path` varchar(100) NOT NULL DEFAULT 'Error',
   `record_id` int NOT NULL,
   PRIMARY KEY (`id`),
   KEY `FK_RecordId` (`record_id`),
   CONSTRAINT `FK_RecordId` FOREIGN KEY (`record_id`) REFERENCES `records` (`id`) ON DELETE CASCADE
 ) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
        cursor.execute(sql)
        dataBase.commit()
        dataBase.close()
    except mysql.connector.Error as error:
        print(format(error))
    finally:
        if dataBase.is_connected():
            cursor.close()
            dataBase.close()
            print("createTable")

def test():
    dataBase = mysql.connector.connect(
      host ="localhost",                # Localhost for local connection
      user ="root",
      passwd ="password",
      database ="db_car"
    )
    query = 'SELECT * FROM records'

    # Execute the query to get the file
    cursor = dataBase.cursor()
    cursor.execute(query)

    data = cursor.fetchall()
    image = data[0][0]
    #nparr = np.fromstring(image, np.uint8)
    img = cv2.imdecode(image, cv2.CV_LOAD_IMAGE_COLOR)
    cv2.imshow("Image", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
#result = getImage("NZ51TSU")
#cv2.imshow("result.jpg", result)
#cv2.waitKey(0)
#cv2.destroyAllWindows()