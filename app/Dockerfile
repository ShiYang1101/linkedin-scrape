FROM public.ecr.aws/lambda/python:3.8

# Install the function's dependencies using file requirements.txt
# from your project folder.

COPY requirements.txt  .
COPY credential ${LAMBDA_TASK_ROOT}
ADD /other_module /other_module

RUN yum update -y
RUN yum install -y python3-devel mysql-devel
RUN yum install -y gcc

RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
RUN pip3 install -e /other_module/scraper/

# Copy function code
COPY app.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "app.lambda_handler" ] 
