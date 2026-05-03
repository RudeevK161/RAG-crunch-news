#!/bin/bash

echo " Деплой RAG системы в Minikube"
echo "================================"


kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f redis.yaml
kubectl apply -f qdrant.yaml
kubectl apply -f api.yaml
kubectl apply -f celery-worker.yaml
kubectl apply -f flower.yaml
kubectl apply -f nginx.yaml
kubectl apply -f ingress.yaml

echo ""
echo "Деплой завершен!"
echo ""
echo "Проверка статуса:"
kubectl get all -n rag-system

echo ""
echo "Доступ к сервисам:"
echo "Flower:  $(minikube service flower-service -n rag-system --url)"
echo "Nginx:   $(minikube service nginx-service -n rag-system --url)"