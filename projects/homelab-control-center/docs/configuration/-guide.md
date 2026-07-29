# RMT Platform Configuration Guide

## Overview

RMT Platform uses layered configuration.

## Configuration Priority

1. Environment variables (.env)
2. YAML configuration
3. Application defaults

## Backend Configuration

Location:

backend/config/config.yaml

Environment:

backend/.env

## Frontend Configuration

Location:

frontend/.env

Variable:

VITE_API_URL

## Migration

To move the platform:

1. Copy configuration templates
2. Create environment files
3. Update API endpoint
4. Restart services
