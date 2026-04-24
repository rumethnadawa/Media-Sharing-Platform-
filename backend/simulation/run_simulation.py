#!/usr/bin/env python3
"""
Backend Simulation and Testing Script
Group A - Media Sharing Platform
Backend Developer: PHDB Nayanakantha

This script simulates the entire backend system including:
- Database operations
- Media service operations
- Queue operations
- Error handling
- End-to-end workflows

Run this script to verify the backend is working correctly.
"""

import sys
import os
import json
import time
from typing import List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import Media, MediaStatus
from app.database import MockDynamoDB
from app.services import MediaService
from app.utils import MockSQS, validate_media_input, validate_media_id


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"{text.center(70)}")
    print(f"{'='*70}{Colors.END}\n")


def print_section(text: str):
    """Print a formatted section."""
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.CYAN}{'-'*len(text)}{Colors.END}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def simulate_database_operations(db: MockDynamoDB) -> bool:
    """
    Simulate database CRUD operations.
    
    Args:
        db: MockDynamoDB instance
        
    Returns:
        True if all operations successful
    """
    print_section("1. Testing Database Operations")
    
    try:
        # Test PUT
        print_info("Testing PUT operation...")
        test_item = {
            'media_id': 'test-001',
            'title': 'Test Video',
            'status': 'pending',
            'file_size': 1024000
        }
        
        if db.put_item('test-001', test_item):
            print_success("PUT operation successful")
        else:
            print_error("PUT operation failed")
            return False
        
        # Test GET
        print_info("Testing GET operation...")
        retrieved = db.get_item('test-001')
        
        if retrieved and retrieved['title'] == 'Test Video':
            print_success("GET operation successful")
        else:
            print_error("GET operation failed")
            return False
        
        # Test UPDATE
        print_info("Testing UPDATE operation...")
        if db.update_item('test-001', {'status': 'processing'}):
            retrieved = db.get_item('test-001')
            if retrieved['status'] == 'processing':
                print_success("UPDATE operation successful")
            else:
                print_error("UPDATE operation verification failed")
                return False
        else:
            print_error("UPDATE operation failed")
            return False
        
        # Test SCAN
        print_info("Testing SCAN operation...")
        all_items = db.scan()
        if len(all_items) >= 1:
            print_success(f"SCAN operation successful (found {len(all_items)} items)")
        else:
            print_error("SCAN operation failed")
            return False
        
        # Test QUERY by status
        print_info("Testing QUERY by status...")
        pending_items = db.query_by_status('pending')
        done_items = db.query_by_status('processing')
        if done_items:
            print_success(f"QUERY by status successful (found {len(done_items)} processing items)")
        
        # Test DELETE
        print_info("Testing DELETE operation...")
        if db.delete_item('test-001'):
            retrieved = db.get_item('test-001')
            if retrieved is None:
                print_success("DELETE operation successful")
            else:
                print_error("DELETE operation verification failed")
                return False
        else:
            print_error("DELETE operation failed")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Database operation error: {e}")
        return False


def simulate_media_service(service: MediaService) -> bool:
    """
    Simulate media service operations.
    
    Args:
        service: MediaService instance
        
    Returns:
        True if all operations successful
    """
    print_section("2. Testing Media Service Operations")
    
    try:
        # Test CREATE
        print_info("Creating test media...")
        success, media, msg = service.create_media(
            title="Sample Video",
            uploader="TestUser",
            object_key="s3://bucket/video.mp4",
            file_size=1024000,
            media_type="video",
            description="A sample video for testing"
        )
        
        if success:
            print_success(f"Media created: {media.media_id}")
            media_id = media.media_id
        else:
            print_error(f"Media creation failed: {msg}")
            return False
        
        # Test GET
        print_info("Retrieving media...")
        success, retrieved_media, msg = service.get_media(media_id)
        
        if success:
            print_success(f"Media retrieved: {retrieved_media.title}")
        else:
            print_error(f"Media retrieval failed: {msg}")
            return False
        
        # Test LIST ALL
        print_info("Listing all media...")
        success, media_list, msg = service.list_all_media()
        
        if success:
            print_success(f"Listed {len(media_list)} media records")
        else:
            print_error(f"Listing failed: {msg}")
            return False
        
        # Test UPDATE STATUS
        print_info("Updating media status...")
        success, msg = service.update_media_status(media_id, 'processing')
        
        if success:
            print_success("Media status updated to processing")
        else:
            print_error(f"Status update failed: {msg}")
            return False
        
        # Test UPDATE PROCESSING
        print_info("Updating media after processing...")
        success, msg = service.update_media_processing(
            media_id,
            thumbnail_key="s3://bucket/thumbs/video_thumb.jpg"
        )
        
        if success:
            print_success("Media processing updated")
        else:
            print_error(f"Processing update failed: {msg}")
            return False
        
        # Verify final state
        success, final_media, msg = service.get_media(media_id)
        if success:
            print_success(f"Final status: {final_media.status}")
            print_success(f"Thumbnail: {final_media.thumbnail_key}")
        
        return True
        
    except Exception as e:
        print_error(f"Media service error: {e}")
        return False


def simulate_queue_operations(queue: MockSQS, service: MediaService) -> bool:
    """
    Simulate queue operations and worker integration.
    
    Args:
        queue: MockSQS instance
        service: MediaService instance
        
    Returns:
        True if all operations successful
    """
    print_section("3. Testing Queue Operations (Worker Integration)")
    
    try:
        # Create a media for processing
        print_info("Creating media for queue processing...")
        success, media, msg = service.create_media(
            title="Video for Processing",
            uploader="ProcessorTest",
            object_key="s3://bucket/process_me.mp4",
            file_size=2048000,
            media_type="video"
        )
        
        if not success:
            print_error(f"Media creation failed: {msg}")
            return False
        
        media_id = media.media_id
        print_success(f"Media created: {media_id}")
        
        # Send message to queue (simulating API sending to worker)
        print_info("Sending processing job to queue...")
        message_body = {
            'media_id': media_id,
            'object_key': media.object_key,
            'action': 'generate_thumbnail'
        }
        
        message_id = queue.send_message(message_body)
        print_success(f"Message sent to queue: {message_id}")
        
        # Check queue size
        queue_size = queue.get_queue_size()
        print_success(f"Queue size: {queue_size} message(s)")
        
        # Simulate worker receiving message
        print_info("Simulating worker processing...")
        messages = queue.receive_messages(max_number=1)
        
        if messages:
            msg_data = json.loads(messages[0]['Body'])
            print_success(f"Worker received message for media: {msg_data['media_id']}")
            
            # Simulate worker updating status
            print_info("Simulating worker updating media status...")
            service.update_media_status(media_id, 'processing')
            print_success("Media status updated to processing")
            
            # Simulate worker completing processing
            print_info("Simulating worker completing processing...")
            success, msg = service.update_media_processing(
                media_id,
                thumbnail_key="s3://bucket/thumbs/process_me_thumb.jpg"
            )
            
            if success:
                print_success("Processing completed, thumbnail generated")
            else:
                print_error(f"Processing update failed: {msg}")
                return False
            
            # Delete message from queue
            print_info("Deleting message from queue...")
            if queue.delete_message(messages[0]['MessageId']):
                print_success(f"Message deleted from queue")
            else:
                print_error("Failed to delete message")
                return False
        else:
            print_error("Worker failed to receive message")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Queue operation error: {e}")
        return False


def simulate_error_handling(service: MediaService) -> bool:
    """
    Simulate error handling scenarios.
    
    Args:
        service: MediaService instance
        
    Returns:
        True if error handling works correctly
    """
    print_section("4. Testing Error Handling")
    
    try:
        # Test invalid media input
        print_info("Testing invalid media input...")
        success, media, msg = service.create_media(
            title="",  # Empty title - should fail
            uploader="TestUser",
            object_key="s3://bucket/test.mp4",
            file_size=1000,
            media_type="video"
        )
        
        if not success:
            print_success("Invalid input properly rejected")
        else:
            print_error("Invalid input was accepted")
            return False
        
        # Test non-existent media
        print_info("Testing retrieval of non-existent media...")
        success, media, msg = service.get_media("invalid-uuid-12345")
        
        if not success:
            print_success("Non-existent media properly handled")
        else:
            print_error("Non-existent media was accepted")
            return False
        
        # Test media processing error
        print_info("Creating media and simulating processing error...")
        success, media, msg = service.create_media(
            title="Error Test Media",
            uploader="ErrorTestUser",
            object_key="s3://bucket/error_test.mp4",
            file_size=1000,
            media_type="video"
        )
        
        if success:
            media_id = media.media_id
            success, msg = service.update_media_processing(
                media_id,
                error_message="Processing failed: Invalid file format"
            )
            
            if success:
                success, error_media, msg = service.get_media(media_id)
                if error_media.is_error():
                    print_success("Error state properly set")
                else:
                    print_error("Error state not set")
                    return False
            else:
                print_error("Failed to set error state")
                return False
        
        return True
        
    except Exception as e:
        print_error(f"Error handling test error: {e}")
        return False


def simulate_statistics(service: MediaService) -> bool:
    """
    Test statistics and reporting.
    
    Args:
        service: MediaService instance
        
    Returns:
        True if statistics work correctly
    """
    print_section("5. Testing Statistics and Reporting")
    
    try:
        print_info("Getting system statistics...")
        stats = service.get_statistics()
        
        print_success("Statistics retrieved:")
        print(f"  {Colors.BLUE}Total Media:{Colors.END} {stats.get('total_media', 0)}")
        print(f"  {Colors.BLUE}Pending:{Colors.END} {stats.get('pending', 0)}")
        print(f"  {Colors.BLUE}Processing:{Colors.END} {stats.get('processing', 0)}")
        print(f"  {Colors.BLUE}Done:{Colors.END} {stats.get('done', 0)}")
        print(f"  {Colors.BLUE}Error:{Colors.END} {stats.get('error', 0)}")
        print(f"  {Colors.BLUE}Total Size (bytes):{Colors.END} {stats.get('total_size_bytes', 0)}")
        
        # Test health check
        print_info("Running health check...")
        if service.health_check():
            print_success("Health check passed")
        else:
            print_error("Health check failed")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Statistics error: {e}")
        return False


def simulate_end_to_end_workflow(service: MediaService, queue: MockSQS) -> bool:
    """
    Simulate a complete end-to-end workflow.
    
    Args:
        service: MediaService instance
        queue: MockSQS instance
        
    Returns:
        True if workflow completes successfully
    """
    print_section("6. End-to-End Workflow Simulation")
    
    try:
        print_info("Simulating complete user workflow...")
        
        # Step 1: User uploads media
        print(f"\n  {Colors.BOLD}Step 1: User uploads media{Colors.END}")
        success, media, msg = service.create_media(
            title="My Vacation Video",
            uploader="john_doe",
            object_key="s3://bucket/vacation/video.mp4",
            file_size=5242880,  # 5MB
            media_type="video",
            description="Beautiful sunset at the beach"
        )
        
        if not success:
            print_error(f"Upload failed: {msg}")
            return False
        
        media_id = media.media_id
        print_success(f"Upload successful. Media ID: {media_id}")
        
        # Step 2: API queues processing job
        print(f"\n  {Colors.BOLD}Step 2: API queues processing job{Colors.END}")
        message_id = queue.send_message({
            'media_id': media_id,
            'object_key': media.object_key,
            'action': 'generate_thumbnail'
        })
        print_success(f"Processing job queued. Message ID: {message_id}")
        
        # Step 3: Worker picks up job
        print(f"\n  {Colors.BOLD}Step 3: Worker picks up job{Colors.END}")
        service.update_media_status(media_id, 'processing')
        print_success("Worker picked up job, status: processing")
        
        # Step 4: Worker processes media (simulate delay)
        print(f"\n  {Colors.BOLD}Step 4: Worker processes media{Colors.END}")
        time.sleep(1)  # Simulate processing time
        print_info("Processing in progress...")
        
        # Step 5: Worker completes processing
        print(f"\n  {Colors.BOLD}Step 5: Worker completes processing{Colors.END}")
        success, msg = service.update_media_processing(
            media_id,
            thumbnail_key="s3://bucket/vacation/video_thumbnail.jpg"
        )
        print_success("Processing complete, thumbnail generated")
        
        # Step 6: User retrieves processed media
        print(f"\n  {Colors.BOLD}Step 6: User retrieves processed media{Colors.END}")
        success, final_media, msg = service.get_media(media_id)
        
        print_success(f"Final Media State:")
        print(f"  {Colors.BLUE}Title:{Colors.END} {final_media.title}")
        print(f"  {Colors.BLUE}Uploader:{Colors.END} {final_media.uploader}")
        print(f"  {Colors.BLUE}Status:{Colors.END} {final_media.status}")
        print(f"  {Colors.BLUE}Thumbnail:{Colors.END} {final_media.thumbnail_key}")
        print(f"  {Colors.BLUE}File Size:{Colors.END} {final_media.file_size} bytes")
        
        # Step 7: Worker removes job from queue
        print(f"\n  {Colors.BOLD}Step 7: Worker removes job from queue{Colors.END}")
        messages = queue.receive_messages()
        if messages:
            queue.delete_message(messages[0]['MessageId'])
            print_success("Job removed from queue")
        
        return True
        
    except Exception as e:
        print_error(f"End-to-end workflow error: {e}")
        return False


def main():
    """Main simulation function."""
    
    # Print header
    print_header("Media Sharing Platform - Backend Simulation")
    
    print_info(f"Backend Developer: PHDB Nayanakantha")
    print_info(f"Project: Group A - Distributed Systems Mini Project")
    print_info(f"Use Case: Media Sharing Platform\n")
    
    # Initialize components
    print_info("Initializing backend components...")
    
    # Initialize database
    db = MockDynamoDB(storage_file="simulation_test_db.json")
    db.clear()  # Start fresh
    print_success("Database initialized")
    
    # Initialize service
    service = MediaService(db)
    print_success("Media service initialized")
    
    # Initialize queue
    queue = MockSQS()
    print_success("Queue initialized")
    
    # Run simulation tests
    tests = [
        ("Database Operations", simulate_database_operations, [db]),
        ("Media Service", simulate_media_service, [service]),
        ("Queue Operations", simulate_queue_operations, [queue, service]),
        ("Error Handling", simulate_error_handling, [service]),
        ("Statistics", simulate_statistics, [service]),
        ("End-to-End Workflow", simulate_end_to_end_workflow, [service, queue])
    ]
    
    results = []
    
    for test_name, test_func, args in tests:
        try:
            print(f"\n{Colors.BOLD}Running test: {test_name}...{Colors.END}")
            result = test_func(*args)
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}PASSED{Colors.END}" if result else f"{Colors.RED}FAILED{Colors.END}"
        print(f"  {test_name}: {status}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.END}\n")
    
    if passed == total:
        print_success("All tests passed! Backend is working correctly.")
        print_info("\nYour backend is ready for integration with:")
        print_info("  - API Developer (L.K.D.H. Perera) - API endpoints")
        print_info("  - Worker/Processor Developer (DMPT Dissanayake) - Processing logic")
        print_info("  - Database Administrator (BDSD Douglas) - Database schema")
        print_info("  - Frontend/DevOps Specialist (KKVRM Kalyanapriya) - Deployment")
        return 0
    else:
        print_error(f"{total - passed} test(s) failed. Please review and fix.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
