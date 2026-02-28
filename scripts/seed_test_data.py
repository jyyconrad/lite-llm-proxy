#!/usr/bin/env python3
"""
Insert sample users, API keys, usage stats, and completion log entries for testing and frontend demo.
Run from repository root:

    python scripts/seed_test_data.py [--users USERS] [--days DAYS] [--entries-per-day ENTRIES_PER_DAY] [--seed SEED]

This script uses the synchronous session helper in `data.db`.
"""
import random
import uuid
import datetime
import hashlib
import argparse
from decimal import Decimal

from data.db import get_sync_session
from data.tables import User, CompletionLog, UsageStat, APIKey
from sqlalchemy.orm import sessionmaker

MODELS = [
    'deepseek-v3.1',
    'Qwen3-Coder-30B-A3B-Instruct',
    'bge-m3'
]

# Extended user information with more comprehensive data
USERS = [
    {
        'id': 'user-1',
        'username': 'alice',
        'email': 'alice@example.com',
        'password_hash': hashlib.sha256(b'password123').hexdigest(),
        'role': 'admin',
        'budget_limit': Decimal('5000.00'),
        'rpm_limit': 100,
        'tpm_limit': 100000,
        'is_active': True
    },
    {
        'id': 'user-2',
        'username': 'bob',
        'email': 'bob@example.com',
        'password_hash': hashlib.sha256(b'password456').hexdigest(),
        'role': 'user',
        'budget_limit': Decimal('1000.00'),
        'rpm_limit': 60,
        'tpm_limit': 60000,
        'is_active': True
    },
    {
        'id': 'user-3',
        'username': 'carol',
        'email': 'carol@example.com',
        'password_hash': hashlib.sha256(b'password789').hexdigest(),
        'role': 'user',
        'budget_limit': Decimal('2000.00'),
        'rpm_limit': 80,
        'tpm_limit': 80000,
        'is_active': True
    },
    {
        'id': 'user-4',
        'username': 'dave',
        'email': 'dave@example.com',
        'password_hash': hashlib.sha256(b'password101').hexdigest(),
        'role': 'user',
        'budget_limit': Decimal('1500.00'),
        'rpm_limit': 70,
        'tpm_limit': 70000,
        'is_active': False
    }
]

def main(args):
    # Set random seed for reproducibility if provided
    if args.seed is not None:
        random.seed(args.seed)
    
    # Determine number of users to create
    num_users = min(args.users, len(USERS))
    selected_users = USERS[:num_users]
    
    session = get_sync_session()
    try:
        # Insert or update users with comprehensive information
        for u in selected_users:
            existing = session.get(User, u['id'])
            if not existing:
                session.add(User(
                    id=u['id'],
                    username=u['username'],
                    email=u['email'],
                    password_hash=u['password_hash'],
                    role=u['role'],
                    budget_limit=u['budget_limit'],
                    rpm_limit=u['rpm_limit'],
                    tpm_limit=u['tpm_limit'],
                    is_active=u['is_active']
                ))
            else:
                # Update existing user with comprehensive information
                existing.username = u['username']
                existing.email = u['email']
                existing.password_hash = u['password_hash']
                existing.role = u['role']
                existing.budget_limit = u['budget_limit']
                existing.rpm_limit = u['rpm_limit']
                existing.tpm_limit = u['tpm_limit']
                existing.is_active = u['is_active']
        session.commit()
        
        # Generate API keys for users
        api_keys = []
        for u in selected_users:
            # Create 1-3 API keys per user
            for i in range(random.randint(1, 3)):
                api_key = APIKey(
                    id=str(uuid.uuid4()),
                    api_key=f"sk-{u['username']}-{uuid.uuid4().hex[:16]}",
                    user_id=u['id'],
                    description=f"API Key {i+1} for {u['username']}",
                    is_active=(i == 0)  # First key is active, others are inactive
                )
                api_keys.append(api_key)
        session.bulk_save_objects(api_keys)
        session.commit()
        
        # Initialize usage stats for each user-model combination if they don't exist
        usage_stats = []
        for u in selected_users:
            for model in MODELS:
                # Check if usage stat already exists
                existing_stat = session.query(UsageStat).filter_by(user_id=u['id'], model_name=model).first()
                if not existing_stat:
                    stat = UsageStat(
                        id=str(uuid.uuid4()),
                        user_id=u['id'],
                        model_name=model,
                        request_count=0,
                        total_tokens=0,
                        total_cost=0
                    )
                    usage_stats.append(stat)
        if usage_stats:
            session.bulk_save_objects(usage_stats)
            session.commit()

        # Insert completion logs across specified number of days
        now = datetime.datetime.now(datetime.timezone.utc)
        completion_logs = []
        usage_updates = {}  # To track usage stats updates
        
        # Initialize usage_updates dictionary
        for u in selected_users:
            for model in MODELS:
                usage_updates[(u['id'], model)] = {'request_count': 0, 'total_tokens': 0, 'total_cost': Decimal('0.000000')}
        
        for day_offset in range(0, args.days):
            for _ in range(args.entries_per_day):
                created = now - datetime.timedelta(days=day_offset, hours=random.randint(0,23), minutes=random.randint(0,59))
                user = random.choice(selected_users)
                model = random.choice(MODELS)
                req_tokens = random.randint(5, 300)
                resp_tokens = random.randint(10, 2000)
                total_tokens = req_tokens + resp_tokens
                # Simple cost model: 0.0001 per token
                cost = 0
                status = 'success' if random.random() > 0.05 else 'error'
                duration = random.randint(100, 5000)  # Random duration between 100ms and 5000ms
                
                entry = CompletionLog(
                    id=str(uuid.uuid4()),
                    user_id=user['id'],
                    model_name=model,
                    request_data={'prompt_length': req_tokens, 'messages': [{'role': 'user', 'content': 'Test message'}]},
                    response_data={'length': resp_tokens} if status == 'success' else None,
                    request_tokens=req_tokens,
                    response_tokens=resp_tokens if status == 'success' else 0,
                    total_tokens=total_tokens if status == 'success' else 0,
                    cost=cost if status == 'success' else Decimal('0.000000'),
                    status=status,
                    error_message=(None if status == 'success' else 'Simulated error'),
                    duration=duration,
                    created_at=created
                )
                completion_logs.append(entry)
                
                # Update usage tracking
                if status == 'success':
                    key = (user['id'], model)
                    usage_updates[key]['request_count'] += 1
                    usage_updates[key]['total_tokens'] += total_tokens
                    usage_updates[key]['total_cost'] += cost

        session.bulk_save_objects(completion_logs)
        session.commit()
        
        # Update usage stats with accumulated data
        for (user_id, model_name), stats in usage_updates.items():
            usage_stat = session.query(UsageStat).filter_by(user_id=user_id, model_name=model_name).first()
            if usage_stat:
                usage_stat.request_count += stats['request_count']
                usage_stat.total_tokens += stats['total_tokens']
                usage_stat.total_cost += stats['total_cost']
        
        session.commit()
        
        print(f"Inserted {len(completion_logs)} CompletionLog entries.")
        print(f"Created {len(api_keys)} API keys for {len(selected_users)} users.")
        print(f"Initialized {len(usage_stats)} UsageStat records.")
        print(f"Ensured {len(selected_users)} users with comprehensive information.")
    except Exception as e:
        # session.rollback()
        raise
    finally:
        session.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed test data for LLM proxy.')
    parser.add_argument('--users', type=int, default=4, help='Number of users to create (default: 4)')
    parser.add_argument('--days', type=int, default=30, help='Number of days of data to generate (default: 30)')
    parser.add_argument('--entries-per-day', type=int, default=10, help='Number of entries per day (default: 10)')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducible data (default: None)')
    
    args = parser.parse_args()
    main(args)