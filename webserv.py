import os
import sys
import socket

port = 0
local_host = "127.0.0.1" 

# extension dictionary
content_types = {
		"txt" 	: "text/plain",
		"html": "text/html",
		"js"	: "application/javascript",
		"css"	: "text/css",
		"png"	: "image/png",
		"jpg"	: "image/jpeg",
		"jpeg"	: "image/jpeg",
		"xml"	: "text/xml"
}

# configuration parser method
def read_config():
    lines = []
    
    try:

        config = open(sys.argv[1], "r")

        # polishing up entries
        temp_lines = config.read().splitlines()
        for l in temp_lines:
            lines.append(l.split("="))
        config.close()

        # making sure no fields are missing
        neccessary_fields = ["staticfiles","cgibin","port","exec"]
        check = []
        for line in lines:
            check.append(line[0])
        contains_all =  all(item in check for item in neccessary_fields)
        if (contains_all == False):
            print("Missing Field From Configuration File")
            sys.exit(1)

        staticfile_directory = lines[0][1]
        cgibin_directory = lines[1][1]
        port = int(lines[2][1].strip())
        exec_program = lines[3][1]
        
        return (staticfile_directory, cgibin_directory, port, exec_program)

    except FileNotFoundError: #other path testing technique? path exists
        print("Unable to load configuration file")
        sys.exit(1)
    # neccessary???
    except IndexError:
        print("Missing Configuration Argument")
        sys.exit(1)
 
    return 

# set up for environment variables in bash
def environment_setup(request):

    every_line = request.split("\n")
    environment_data = {
        "HTTP_HOST":"null",
        "HTTP_USER_AGENT":"null",
        "HTTP_ACCEPT_ENCODING":"null",
        "REMOTE_ADDRESS":"null",
        "REMOTE_PORT":"null",
        "REQUEST_METHOD":"null",
        "REQUEST_URI":"null",
        "SERVER_ADDR":"null",
        "SERVER_PORT":"null",
        "CONTENT_TYPE":"null",
        "CONTENT_LENGTH":"null",
        "QUERY_STRING":"null"}

    request_url = "".join(every_line[0].split(" ")[1].split("?"))
    request_uri = request_url[:1]
    query_string = request_url[1:]
    request_method = every_line[0].split(" ")[0]

    os.environ["REQUEST_URI"] = request_uri
    os.environ["REQUEST_METHOD"] = request_method
    os.environ["QUERY_STRING"] = query_string
    os.environ["SERVER_ADDR"] = "127.0.0.1" 
    os.environ["SERVER_PORT"] = str(port)


    #environment_data["REQUEST_METHOD"] = request_method #this is like GET
    #environment_data["REQUEST_URI"] = request_uri #resource upon which to apply request, url as given in html
    #environment_data["QUERY_STRING"] = query_string
    
    #environment_data["SERVER_ADDR"] = "127.0.0.1" 
    #environment_data["SERVER_PORT"] = port
    #os.environ["SERVER_PORT"] = port
    #going through the body of request
    for line in request[1:]:

        if line[0] == "Host":
            os.environ["HTTP_HOST"] = line[1][1:]
        elif line[0] == "User-Agent":
            os.environ["HTTP_USER_AGENT"] = line[1][1:]
        elif line[0] == "Accept":
            os.environ["HTTP_ACCEPT"] = line[1][1:]
        elif line[0] == "Accept-Encoding":
            os.environ["HTTP_ACCEPT_ENCODING"] = line[1][1:]
        elif line[0] == "Remote-Address":
            os.environ["REMOTE_ADDRESS"] = line[1][1:]
        elif line[0] == "Content-Type":
            os.environ["CONTENT_TYPE"] = line[1][1:]
        elif line[0] == "Content-Length":
            os.environ["CONTENT_LENGTH"] = line[1][1:]    
    
    #for key, value in environment_data.items():
        
       # os.environ[str(value)] = str(key)
    
#status message
def status_200(file_extension, file):

    output = "HTTP/1.1 200 OK\n"
    output += "Content Type: {}\n\n".format(file_extension)
    data = ""
    lines = file.readlines()
    for line in lines:
        data += line

    output += data
    return output

#status message
def status_404(file_extension):
    output = "HTTP/1.1 404 File not found\n"
    output += "Content-Type: {}\n\n".format(file_extension)
    output += "<html>\n"
    output += "<head>\n\t<title>404 Not Found</title>\n</head>\n"
    output += '<body bgcolor="white">\n'
    output += "<center>\n\t<h1>404 Not Found</h1>\n</center>\n"
    output += "</body>\n"
    output += "</html>\n"
    return output
   
#status message
def status_505(file_extension):
    output = "HTTP/1.1 500 Internal Server Error\n\r\n"
    output += "Content-Type: {}\n\n".format(file_extension)
    output += """500 Internal Server Error\n\n<html>\n<head>\n\t<title>500 Internal Server 
            Error</title>\n</head><body bgcolor="white">\n<center>\n\t<h1>500 Internal
             Server Error</h1>\n</center>\n</body>\n</html>\n"""
    return output
              
#cgi set up method
def cgi(client, file_extension, filepath, execpath):
    #create a pipe 
    r, w = os.pipe() 

    #creating grandchild process
    pid_grandchild = os.fork()

    #refering to parent
    if pid_grandchild > 0:
        #read pipe from grandchild and sent to client
        data_read = os.read(r, 1024).decode()
        os.close(w)
        os.close(r)
        #client.send(status_200(" ", data_read).encode())
        client.send("HTTP/1.1 200 OK\n".encode())

        #if not("Content-Type" in data_read):
         #  client.send("Content-Type: \n".encode())
        #client.send("\n".encode())
        client.sendall(data_read.encode())
        client.close()
        #data = os.read(r)
        #client.sendall(data.encode("atf-8"))
        #os.close(r)
        
    #referring to grandchild process
    elif pid_grandchild == 0:
        #write to pipe
        os.dup2(w,1)
        if (os.path.isfile(filepath)):
            try:
                os.execv(execpath, (execpath, filepath))
            except FileNotFoundError:
                os.close(w)
                os.close(r)
                client.send(status_505(file_extension).encode())
            finally:
                client.close()
        else:
            client.send(status_505(file_extension).encode())
            client.close()

    #error recieved
    else:
        client.close()

#main method
def main():
    staticfile_directory, cgibin_directory, port, exec_program =read_config()
    
    # set up server connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    server.bind(("127.0.0.1", port)) 
    server.listen()

    # start listening for connection
    while True:
        accept_results = server.accept()
        client = accept_results[0]
        addr = accept_results[1]
        
        #entire html request
        request = client.recv(1024).decode()
       
        #first line key info
        first_line = request.split("/n")[0].split()
        method = first_line[0]
        resource_name = first_line[1]
        protocol = first_line[2]

        if resource_name.strip() == "/":
            resource = "index.html" ### ON THE DAY, PUT AS "./{}/index.html".format(info_tup[0])
            extension = "html"
        else:
            #keyline for identifying if cgi or static
            resource = resource_name.lstrip("/")

            #identifying neccessary extension
            temp = resource.split(".")[1:]
            extension = " ".join(temp)
     
        #creating a new process
        pid = os.fork()

        # if child process
        if pid == 0:
            
            if extension in content_types:
                        file_extension = content_types[extension]

            #getting filename for if static file
            file_name = "./files/" + resource
            
            #set enviroment variables
            

            #if static file
            if "cgibin" not in resource:
                
                binary_possibilities = ["image/png", "image/jpeg"]
                
                #checking if exists or not
                try:
                    if extension in binary_possibilities:
                        with open(file_name, "rb") as file:
                            client.send(status_200(file_extension, file).encode())
                    else:
                        with open(file_name, "r") as file:
                            every_line = file.readlines
                            
                            if not("Content-Type" in every_line[0]):
                                client.send("HTTP/1.1 200 OK\n".encode())
                                client.send(f'Content-Type: {file_extension}\n'.encode())
                                client.send('\n'.encode())
                                for line in every_line:
                                    client.send(line.encode())
                            else:
                                client.send(status_200(file_extension, file).encode())
                            file.close()    
                            #need to do the content type checking 
                            
                except FileNotFoundError:
                    
                    client.send(status_404(file_extension).encode())
                
                finally:
                    client.close()

            #if its a cgi file
            if "cgibin" in resource:

                environment_setup(request)
                resource= "".join(resource.split("/")[1:]) 
                file_extension = resource.split(".")[1]

                file_path = "./cgibin/{}".format(resource)
                exec_program = exec_program.strip()
                cgi(client, file_extension, file_path, exec_program)

        #parent process
        elif pid > 0:
            client.close()

        #error
        elif pid < 0:
            client.close()
            sys.exit(1)

if __name__ == '__main__':
    main()
