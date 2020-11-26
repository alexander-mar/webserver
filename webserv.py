import os
import sys
import socket


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
        neccessary_fields = ["staticfiles", "cgibin", "port", "exec"]
        check = []
        for line in lines:
            check.append(line[0])

        contains_all = all(item in check for item in neccessary_fields)
        if (contains_all == False):
            print("Missing Field From Configuration File")
            sys.exit(1)

        staticfile_directory = lines[0][1]
        cgibin_directory = lines[1][1]
        port = int(lines[2][1].strip())
        exec_program = lines[3][1]

        return (staticfile_directory, cgibin_directory, port, exec_program)

    # if cant find file
    except FileNotFoundError:  
        print("Unable to load configuration file")
        sys.exit(1)

    # if missing an argument
    except IndexError:
        print("Missing Configuration Argument")
        sys.exit(1)

    return

# set up for environment variables in bash
def environment_setup(request, port):

    every_line = request.split("\n")
    request_url = "".join(every_line[0].split(" ")[1].split("?"))
    temp = every_line[0].split(" ")[1].split("?")[:1]
    request_uri = "".join(temp)
    query_string = request_url[1:]
    request_method = every_line[0].split(" ")[0]

    os.environ["REQUEST_URI"] = request_uri
    os.environ["REQUEST_METHOD"] = request_method
    os.environ["QUERY_STRING"] = query_string
    os.environ["SERVER_ADDR"] = "127.0.0.1"
    os.environ["SERVER_PORT"] = str(port)

    # going through the body of request
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

# status message
def status_200(file_extension, file):

    out = "HTTP/1.1 200 OK\n"
    out += "Content Type: {}\n\n".format(file_extension)
    data = ""

    if not isinstance(file, str):
        lines = file.readlines()
        for line in lines:
            data += line
        out += data
    else:
        out = file

    return out

# status message
def status_404(file_extension):
    out = "HTTP/1.1 404 File not found\n"
    out += "Content-Type: {}\n\n".format(file_extension)
    out += "<html>\n"
    out += "<head>\n\t<title>404 Not Found</title>\n</head>\n"
    out += '<body bgcolor="white">\n'
    out += "<center>\n\t<h1>404 Not Found</h1>\n</center>\n"
    out += "</body>\n"
    out += "</html>\n"
    return out

# status message
def status_505(file_extension):
    out = "HTTP/1.1 500 Internal Server Error\n\r\n"
    out += "Content-Type: {}\n\n".format(file_extension)
    out += """500 Internal Server Error\n\n<html>\n<head>\n\t<title>500 Internal Server 
            Error</title>\n</head><body bgcolor="white">\n<center>\n\t<h1>500 Internal
             Server Error</h1>\n</center>\n</body>\n</html>\n"""
    return out

# cgi handler
def cgi(client, file_extension, filepath, execpath):

    # setting up
    content_read = ""
    status = ""
    head = ""

    # create a pipe, and process
    r, w = os.pipe()
    pid_grandchild = os.fork()

    # referring to grandchild process
    if pid_grandchild == 0:
        os.close(r)
        # write to pipe
        os.dup2(w, 1)
        os.dup2(w, 2)

        if (os.path.isfile(filepath)):
            try:
                os.execv(execpath, (execpath, filepath))

            except FileNotFoundError:
                os._exit(0)

            finally:
                client.close()

            os._exit(0)

    # refering to parent process
    elif pid_grandchild > 0:

        content_read = os.read(r, 1024).decode().split("\n")
        os.close(w)
        os.close(r)
        wait = os.wait()
        if (wait[1] != 0):
            client.send("HTTP/1.1 500 Internal Server Error".encode())
            client.close()

    # error recieved
    else:
        client.send("HTTP/1.1 500 Internal Server Error".encode())
        client.close()

    # preparing message
    i = 0
    while(i < len(content_read)):
        if("Status-Code" in content_read[i]):
            codes = content_read[i].split(" ", 2)
            status = "HTTP/1.1 {} {}\n".format(codes[1], codes[2])
        elif("Content-Type" in content_read[i]):
            head = content_read[i]
        else:
            break
        i += 1
    
    if i > 0:
        content_read = content_read[i+1:]

    processed_info = "\n".join(content_read), head, status

    message = ""
    if(processed_info[2] == ""):
        message += "HTTP/1.1 200 OK\n"
    else:
        message += processed_info[2]
    if(processed_info[2] == ""):
        message += "Content-Type: {}\n\n".format(os.environ.get("CONTENT_TYPE"))
    else:
        message += processed_info[1]
    for line in processed_info[0]:
        message += line

    client.sendall(message.encode())


# main method
def main():
    
    info = read_config()
    port = info[2]
    exec_program = info[3]

    # set up server connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen()

    # start listening for connection
    while True:
        accept_results = server.accept()
        client = accept_results[0]

        # entire html request
        request = client.recv(1024).decode()

        # first line key info
        first_line = request.split("/n")[0].split()
        resource_name = first_line[1]

        if resource_name.strip() == "/":
            
            resource = "index.html"
            extension = "html"
        else:
            # keyline for identifying if cgi or static
            resource = resource_name.lstrip("/")

            # identifying neccessary extension
            temp = resource.split(".")[1:]
            extension = " ".join(temp)

        # creating a new process
        pid = os.fork()

        # if child process
        if pid == 0:

            if extension in content_types:
                file_extension = content_types[extension]

            # getting filename for if static file
            file_name = "./files/" + resource

            # if static file
            if "cgibin" not in resource:

                binary_possibilities = ["image/png", "image/jpeg"]

               
                try:
                    if extension in binary_possibilities:
                        # binary 
                        with open(file_name, "rb") as file:
                            client.send(status_200(file_extension, file).encode())
                    else:
                        # non binary
                        with open(file_name, "r") as file:
                            every_line = file.readlines()
                            
                            if "Content-Type" in every_line[0]:
                                client.send(status_200(file_extension, file).encode())
                            else:
                                client.send("HTTP/1.1 200 OK\n".encode())
                                client.send(f'Content-Type: {file_extension}\n'.encode())
                                client.send('\n'.encode())
                                for line in every_line:
                                    client.send(line.encode())

                except FileNotFoundError:
                    client.send(status_404(file_extension).encode())

                except BrokenPipeError:
                    pass

                finally:
                    client.close()

            # if its a cgi file
            if "cgibin" in resource:

                environment_setup(request, port)
                resource = "".join(resource.split("/")[1:])
                file_extension = resource.split(".")[1]
                file_path = "./cgibin/{}".format(resource)
                exec_program = exec_program.strip()

                cgi(client, file_extension, file_path, exec_program)

        # parent process
        elif pid > 0:
            client.close()

        # error
        elif pid < 0:
            client.close()
            sys.exit(-1)

        client.close()


if __name__ == '__main__':
    main()
