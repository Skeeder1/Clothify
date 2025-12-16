.PHONY: help start stop restart down clean logs logs-pg ps connect shell status launch-azure stop-azure chartdb-start chartdb-stop chartdb-status

# Default target
.DEFAULT_GOAL := help

# Load environment variables
include .env
export

help: ## Afficher toutes les commandes disponibles
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║         Clothify - Base de données PostgreSQL                ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📋 Commandes principales:"
	@echo ""
	@grep -hE '^(start|stop|restart|status|help):.*## ' $(MAKEFILE_LIST) | awk -F ':[[:space:]]*## ' '{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🗄️  Commandes PostgreSQL:"
	@echo ""
	@grep -hE '^(connect|shell|logs|logs-pg|ps):.*## ' $(MAKEFILE_LIST) | awk -F ':[[:space:]]*## ' '{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "💻 Commandes Azure Data Studio:"
	@echo ""
	@grep -hE '^(launch-azure|stop-azure):.*## ' $(MAKEFILE_LIST) | awk -F ':[[:space:]]*## ' '{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "📊 ChartDB - Editeur de diagrammes:"
	@echo ""
	@grep -hE '^(chartdb-start|chartdb-stop|chartdb-status):.*## ' $(MAKEFILE_LIST) | awk -F ':[[:space:]]*## ' '{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🧹 Commandes de maintenance:"
	@echo ""
	@grep -hE '^(down|clean):.*## ' $(MAKEFILE_LIST) | awk -F ':[[:space:]]*## ' '{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

start: ## Démarrer PostgreSQL
	@echo "🚀 Démarrage de PostgreSQL..."
	docker compose up -d
	@echo "✅ PostgreSQL démarré!"
	@make --no-print-directory status

stop: ## Arrêter tous les services
	@echo "🛑 Arrêt des services Docker..."
	docker compose stop
	@echo "✅ Services arrêtés!"

restart: ## Redémarrer les services
	@echo "🔄 Redémarrage des services..."
	docker compose restart
	@echo "✅ Services redémarrés!"

down: ## Arrêter et supprimer les conteneurs (garde les données)
	@echo "⬇️  Arrêt et suppression des conteneurs..."
	docker compose down
	@echo "✅ Conteneurs supprimés (données conservées)!"

clean: ## Tout supprimer (conteneurs + volumes/données) ⚠️ DANGER
	@echo "⚠️  ATTENTION: Cette action supprimera TOUTES les données!"
	@read -p "Êtes-vous sûr? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker compose down -v; \
		echo "✅ Tout a été supprimé!"; \
	else \
		echo "❌ Opération annulée."; \
	fi

logs: ## Voir les logs en temps réel
	docker compose logs -f

logs-pg: ## Logs PostgreSQL uniquement
	docker compose logs -f postgres

ps: ## Voir le statut des conteneurs
	@docker compose ps

connect: ## Se connecter à PostgreSQL via psql
	@echo "🔌 Connexion à PostgreSQL..."
	@echo "Database: ${POSTGRES_DB}"
	@docker exec -it postgres_clothify psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

shell: ## Ouvrir un shell dans le conteneur PostgreSQL
	@echo "🐚 Ouverture du shell..."
	@docker exec -it postgres_clothify bash

status: ## Afficher l'état des services et les URLs d'accès
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║                    État des services                         ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@docker compose ps
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║                    Points d'accès                            ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🗄️  PostgreSQL:"
	@echo "   Host:     localhost"
	@echo "   Port:     5432"
	@echo "   Database: ${POSTGRES_DB}"
	@echo "   User:     ${POSTGRES_USER}"
	@echo "   Password: ${POSTGRES_PASSWORD}"
	@echo ""
	@echo "📊 ChartDB:"
	@if docker ps --format '{{.Names}}' | grep -q '^chartdb$$'; then \
		echo "   Status:   ✅ En cours sur http://localhost:5000"; \
	else \
		echo "   Status:   ⏸️  Arrêté (lancez avec 'make chartdb-start')"; \
	fi
	@echo ""

# ============================================================================
# Azure Data Studio
# ============================================================================

launch-azure: ## Lancer Azure Data Studio
	@echo "🚀 Lancement d'Azure Data Studio..."
	@if command -v azuredatastudio &> /dev/null; then \
		if pgrep -f azuredatastudio > /dev/null; then \
			echo "✅ Azure Data Studio est déjà en cours d'exécution"; \
		else \
			nohup azuredatastudio > /dev/null 2>&1 & \
			sleep 2; \
			echo "✅ Azure Data Studio lancé!"; \
		fi; \
	else \
		echo "⚠️  Azure Data Studio n'est pas installé."; \
	fi

stop-azure: ## Arrêter Azure Data Studio
	@echo "🛑 Arrêt d'Azure Data Studio..."
	@pkill -f azuredatastudio 2>/dev/null && echo "✅ Azure Data Studio arrêté!" || echo "   Azure Data Studio n'était pas en cours d'exécution"

# ============================================================================
# ChartDB - Database Diagrams Editor
# ============================================================================

chartdb-start: ## Démarrer ChartDB (http://localhost:5000)
	@if docker ps --format '{{.Names}}' | grep -q '^chartdb$$'; then \
		echo "✅ ChartDB est déjà en cours d'exécution sur http://localhost:5000"; \
	else \
		echo "🚀 Démarrage de ChartDB..."; \
		docker start chartdb 2>/dev/null || docker run -d --name chartdb -p 5000:80 ghcr.io/chartdb/chartdb:latest; \
		echo "✅ ChartDB démarré sur http://localhost:5000"; \
	fi

chartdb-stop: ## Arrêter ChartDB
	@if docker ps --format '{{.Names}}' | grep -q '^chartdb$$'; then \
		echo "🛑 Arrêt de ChartDB..."; \
		docker stop chartdb; \
		echo "✅ ChartDB arrêté!"; \
	else \
		echo "⏸️  ChartDB n'est pas en cours d'exécution"; \
	fi

chartdb-status: ## Voir le statut de ChartDB
	@if docker ps --format '{{.Names}}' | grep -q '^chartdb$$'; then \
		echo "✅ ChartDB: En cours sur http://localhost:5000"; \
	else \
		echo "⏸️  ChartDB: Arrêté"; \
	fi
