"""Punto de entrada: uvicorn main:app --reload"""
from presentation.app import crear_app

app = crear_app()
