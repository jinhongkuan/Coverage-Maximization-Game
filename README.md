# Coverage Maximization Game
 This is an undergraduate research project aimed at investigating the dynamics of human-AI collaboration. It is written in Python with the Django library, and can be hosted as a web application.

 # Installation
 ## On Local Machine 
 Ensure that Python3.x and pip is installed on the computer. For more information, refer to https://www.python.org/
 1. This project requires virtualenv to be run. To acquire the virtualenv Python library:
 ```sh
 sudo pip install virtualenv
 ```
2. Run the virtual environment:
```sh
cd [project directory]
venv 
```
3. To prepare the database for the first time / reset the database:
```sh 
python manage.py makemigrations
python manage.py migrate 
python manage.py flush 
python manage.py shell < clear_all.py
```

4. To host the web-app on local machine:
```sh 
python manage.py runserver 
```

5. Access the game at 127.0.0.1. Note that since it is a multiplayer game, hosting on a local machine does not allow other players to join the game.  

## On Server 
This webapp can be hosted on any server that provides database service (required because multiplayer game demands high concurrency)

The guide below shows the specifics of hosting on Amazon ElasticBeanstalk service 

1. Create an Elastic Beanstalk environment: https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/GettingStarted.html?icmpid=docs_elasticbeanstalk_console

2. Create a MySQL database: https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.managing.db.html. Make sure to set Availability to High to support high number of players. 

3. Install awsebcli on computer to interface with the server: https://github.com/aws/aws-elastic-beanstalk-cli-setup

4. Configure elasticbeanstalk to work with the project: https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-configuration.html. Agree to setting up ssh. 

5. Update the ALLOWED_HOST and DATABASE field in the settings file (.../cov-max/covmax/settings.py) to work with the server 

6. Deploy the app to the server:
```sh
cd [project directory]
eb deploy 
```

7. SSH into the server:
```sh
eb ssh
```

8. Run virtual environment on the server:
```sh 
source /opt/python/run/venv/bin/activate 
```

9. To prepare the database for the first time / reset the database:
```sh
cd /opt/python/current/app/
python manage.py makemigrations
python manage.py migrate 
python manage.py flush 
python manage.py shell < clear_all.py
``` 

10. Run the webapp on the server:
```sh 
python manage.py runserver 
```