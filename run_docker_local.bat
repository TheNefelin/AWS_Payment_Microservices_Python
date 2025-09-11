
REM --------------------------------------------------------
REM Construir y levantar Imagen micropay-auth-service-repo
REM --------------------------------------------------------
docker build -f auth_microservice/Dockerfile -t micropay-auth-service-repo ./auth_microservice
docker run -d -p 8000:8000 --env-file auth_microservice/.env --name micropay-auth micropay-auth-service-repo

REM --------------------------------------------------------
REM Construir y levantar Imagen micropay-notifications-service-repo
REM --------------------------------------------------------
docker build -f notifications_microservce/Dockerfile -t micropay-notifications-service-repo ./notifications_microservce
docker run -d -p 8000:8000 --env-file notifications_microservce/.env --name micropay-notifications micropay-notifications-service-repo

echo Contenedores levantados!
pause