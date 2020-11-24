import os
import sys
import socket

port = 0
local_host = ""

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
        port = int(lines[2][1])
        exec_program = lines[3][1]
        local_host = "127.0.0.1" 

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

    first_line = request[0].split(" ")
    environment_data["REQUEST_METHOD"] = first_line[0] #this is like GET
    query = first_line[1].split("?")
    environment_data["REQUEST_URI"] = query[0] #resource upon which to apply request, url as given in html

    environment_data["SERVER_ADDR"] = "127.0.0.1" #set up so that can access these
    environment_data["SERVER_PORT"] = port

    #going through the body and not the header now
    for line in request[1:]:

        if line[0] == "Host":
            environment_data["HTTP_HOST"] = line[1][1:]
        elif line[0] == "User-Agent":
            environment_data["HTTP_USER_AGENT"] = line[1][1:]
        elif line[0] == "Accept":
            environment_data["HTTP_ACCEPT"] = line[1][1:]
        elif line[0] == "Accept-Encoding":
            environment_data["HTTP_ACCEPT_ENCODING"] = line[1][1:]
        elif line[0] == "Remote-Address":
            environment_data["REMOTE_ADDRESS"] = line[1][1:]
        elif line[0] == "Content-Type":
            environment_data["CONTENT_TYPE"] = line[1][1:]
        elif line[0] == "Content-Length":
            environment_data["CONTENT_LENGTH"] = line[1][1:]
        #Is setting the query string neccesary

    before, after = first_line[1].split("?")
    environment_data["QUERY_STRING"] = after

    for key, value in environment_data.items():
        os.environ[value] = key
    
#status message
def status_200(file_extension, file):
    print("a")
    output = "HTTP/1.1 200 OK\n"
    output += "Content Type: {}\n\n".format(file_extension)
    data = ""
    lines = file.readlines()
    for line in lines:
        data += line+"\n"

    output += data
    return output

#status message
def status_404(file_extension):
	output = "HTTP/1.1 404 Not Found\n"
	output += "Content-Type: {}\n\n".format(file_extension)
	output += "<html>\n"
	output += "<head><title>404 Not Found</title></head>\n"
	output += "<body>\n"
	output += "    <h1>404 Not Found</h1>\n"
	output += "</body>\n"
	output += "</html>\n"
	return output

#main method
def main():
    print("b")
    read_config()
    
    # set up server connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    server.bind(("127.0.0.1", port)) 
    server.listen()

    # start listening for connection
    while True:
        print("b")
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
        print("x")
        #creating a new process
        pid = os.fork()

        # if child process
        if pid == 0:
            
            #keyline for identifying if cgi or static
            resource = resource_name.lstrip("/")

            #identifying neccessary extension
            extension = "".join(resource.split("."[1:]))
            if extension in content_types:
                        file_extension = content_types[extension]

            #getting filename for if static file
            file_name = "./files/" + resource + "."

            #set enviroment variables
            environment_setup(request)

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
                            client.send(status_200(file_extension, file).encode())
                            #need to do the content type checking 
                            
                except FileNotFoundError:
                    client.send(status_404(file_extension).encode())
                
                finally:
                    client.close()
        
        #parent process
        elif pid > 0:
            client.close()

        #error
        elif pid < 0:
            client.close()
            sys.exit(1)

if __name__ == '__main__':
    main()
