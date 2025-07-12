import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.models.trip import ItineraryDay, Activity, ActivityType
from src.models.user import UserProfile, BudgetLevel, TravelPace


@dataclass
class CritiqueResult:
    """Result of itinerary critique."""
    approved: bool
    score: float
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    summary: str


class CritiqueAgent(BaseAgent):
    """Agent responsible for quality assurance of proposed itineraries."""
    
    def __init__(self):
        super().__init__(
            agent_id="critique",
            name="Itinerary Critic",
            description="Reviews proposed itineraries for logical flaws, budget alignment, and user profile matching",
            tools=[]  # Calculator functionality is built-in
        )
        
        # Quality thresholds
        self.quality_thresholds = {
            "minimum_score": 70,  # Minimum score for approval
            "maximum_travel_time_ratio": 0.4,  # Max 40% of day spent traveling
            "minimum_activity_duration": 30,  # Minimum 30 minutes per activity
            "maximum_activity_duration": 240,  # Maximum 4 hours per activity
            "reasonable_day_length": 12 * 60,  # 12 hours maximum day length
            "minimum_break_time": 15,  # Minimum 15 minutes between activities
        }
        
        # Budget estimates per activity type (in USD)
        self.activity_cost_estimates = {
            ActivityType.DINING: {"budget": 15, "mid-range": 30, "luxury": 80},
            ActivityType.SIGHTSEEING: {"budget": 10, "mid-range": 20, "luxury": 50},
            ActivityType.CULTURAL: {"budget": 12, "mid-range": 25, "luxury": 60},
            ActivityType.ENTERTAINMENT: {"budget": 20, "mid-range": 40, "luxury": 100},
            ActivityType.SHOPPING: {"budget": 30, "mid-range": 100, "luxury": 300},
            ActivityType.OUTDOOR: {"budget": 5, "mid-range": 15, "luxury": 40},
            ActivityType.TRANSPORT: {"budget": 10, "mid-range": 20, "luxury": 50}
        }
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are a meticulous travel plan critic. Your role is to ensure every itinerary is:
        1. Logically consistent and feasible
        2. Properly aligned with the user's budget
        3. Matched to the user's travel profile and preferences
        4. Optimized for time and travel efficiency
        5. Realistic and executable
        
        Review each itinerary thoroughly and provide constructive feedback for improvement.
        Only approve itineraries that meet high quality standards.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the critique agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "critique_itinerary":
            return await self._critique_itinerary(content)
        elif message_type == "validate_budget":
            return await self._validate_budget(content)
        elif message_type == "check_feasibility":
            return await self._check_feasibility(content)
        elif message_type == "analyze_profile_match":
            return await self._analyze_profile_match(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _critique_itinerary(self, content: Dict[str, Any]) -> AgentResponse:
        """Perform comprehensive critique of an itinerary."""
        try:
            # Parse inputs
            itinerary_data = content.get("itinerary")
            user_profile_data = content.get("user_profile")
            
            if not itinerary_data or not user_profile_data:
                return self._create_error_response("itinerary and user_profile are required")
            
            # Create objects
            itinerary = ItineraryDay(**itinerary_data)
            user_profile = UserProfile(**user_profile_data)
            
            # Perform comprehensive critique
            critique_result = await self._perform_comprehensive_critique(itinerary, user_profile)
            
            return self._create_success_response({
                "critique_result": {
                    "approved": critique_result.approved,
                    "score": critique_result.score,
                    "issues": critique_result.issues,
                    "recommendations": critique_result.recommendations,
                    "summary": critique_result.summary
                },
                "detailed_analysis": await self._generate_detailed_analysis(itinerary, user_profile, critique_result)
            })
            
        except Exception as e:
            self.logger.error(f"Error critiquing itinerary: {str(e)}")
            return self._create_error_response(f"Failed to critique itinerary: {str(e)}")
    
    async def _validate_budget(self, content: Dict[str, Any]) -> AgentResponse:
        """Validate itinerary against budget constraints."""
        try:
            itinerary_data = content.get("itinerary")
            user_profile_data = content.get("user_profile")
            
            itinerary = ItineraryDay(**itinerary_data)
            user_profile = UserProfile(**user_profile_data)
            
            budget_analysis = await self._analyze_budget(itinerary, user_profile)
            
            return self._create_success_response(budget_analysis)
            
        except Exception as e:
            self.logger.error(f"Error validating budget: {str(e)}")
            return self._create_error_response(f"Failed to validate budget: {str(e)}")
    
    async def _check_feasibility(self, content: Dict[str, Any]) -> AgentResponse:
        """Check logical feasibility of itinerary."""
        try:
            itinerary_data = content.get("itinerary")
            itinerary = ItineraryDay(**itinerary_data)
            
            feasibility_analysis = await self._analyze_feasibility(itinerary)
            
            return self._create_success_response(feasibility_analysis)
            
        except Exception as e:
            self.logger.error(f"Error checking feasibility: {str(e)}")
            return self._create_error_response(f"Failed to check feasibility: {str(e)}")
    
    async def _analyze_profile_match(self, content: Dict[str, Any]) -> AgentResponse:
        """Analyze how well itinerary matches user profile."""
        try:
            itinerary_data = content.get("itinerary")
            user_profile_data = content.get("user_profile")
            
            itinerary = ItineraryDay(**itinerary_data)
            user_profile = UserProfile(**user_profile_data)
            
            profile_analysis = await self._analyze_profile_alignment(itinerary, user_profile)
            
            return self._create_success_response(profile_analysis)
            
        except Exception as e:
            self.logger.error(f"Error analyzing profile match: {str(e)}")
            return self._create_error_response(f"Failed to analyze profile match: {str(e)}")
    
    async def _perform_comprehensive_critique(self, itinerary: ItineraryDay, user_profile: UserProfile) -> CritiqueResult:
        """Perform comprehensive critique of itinerary."""
        issues = []
        recommendations = []
        scores = []
        
        # 1. Check logical consistency
        logic_result = await self._check_logical_consistency(itinerary)
        scores.append(logic_result["score"])
        issues.extend(logic_result["issues"])
        recommendations.extend(logic_result["recommendations"])
        
        # 2. Check budget alignment
        budget_result = await self._analyze_budget(itinerary, user_profile)
        scores.append(budget_result["score"])
        issues.extend(budget_result["issues"])
        recommendations.extend(budget_result["recommendations"])
        
        # 3. Check profile alignment
        profile_result = await self._analyze_profile_alignment(itinerary, user_profile)
        scores.append(profile_result["score"])
        issues.extend(profile_result["issues"])
        recommendations.extend(profile_result["recommendations"])
        
        # 4. Check time feasibility
        time_result = await self._analyze_time_feasibility(itinerary)
        scores.append(time_result["score"])
        issues.extend(time_result["issues"])
        recommendations.extend(time_result["recommendations"])
        
        # 5. Check activity quality
        quality_result = await self._analyze_activity_quality(itinerary)
        scores.append(quality_result["score"])
        issues.extend(quality_result["issues"])
        recommendations.extend(quality_result["recommendations"])
        
        # Calculate overall score
        overall_score = sum(scores) / len(scores) if scores else 0
        
        # Determine approval
        approved = (
            overall_score >= self.quality_thresholds["minimum_score"] and
            len([i for i in issues if i.get("severity") == "high"]) == 0
        )
        
        # Generate summary
        summary = self._generate_critique_summary(overall_score, issues, approved)
        
        return CritiqueResult(
            approved=approved,
            score=overall_score,
            issues=issues,
            recommendations=recommendations,
            summary=summary
        )
    
    async def _check_logical_consistency(self, itinerary: ItineraryDay) -> Dict[str, Any]:
        """Check logical consistency of the itinerary."""
        issues = []
        recommendations = []
        score = 100
        
        activities = itinerary.activities
        
        # Check for overlapping activities
        for i in range(len(activities) - 1):
            current = activities[i]
            next_activity = activities[i + 1]
            
            if current.end_time and next_activity.start_time:
                if current.end_time > next_activity.start_time:
                    issues.append({
                        "type": "time_overlap",
                        "severity": "high",
                        "description": f"Activity '{current.name}' overlaps with '{next_activity.name}'",
                        "activities": [current.name, next_activity.name]
                    })
                    score -= 20
        
        # Check for impossible travel times
        for i in range(len(activities) - 1):
            current = activities[i]
            next_activity = activities[i + 1]
            
            if next_activity.travel_time_from_previous:
                expected_travel_time = next_activity.travel_time_from_previous
                
                if current.end_time and next_activity.start_time:
                    actual_gap = (next_activity.start_time - current.end_time).total_seconds() / 60
                    
                    if actual_gap < expected_travel_time:
                        issues.append({
                            "type": "insufficient_travel_time",
                            "severity": "high",
                            "description": f"Insufficient travel time between '{current.name}' and '{next_activity.name}'",
                            "expected_minutes": expected_travel_time,
                            "actual_minutes": actual_gap
                        })
                        score -= 15
        
        # Check for unreasonable activity durations
        for activity in activities:
            if activity.duration_minutes:
                if activity.duration_minutes < self.quality_thresholds["minimum_activity_duration"]:
                    issues.append({
                        "type": "too_short_activity",
                        "severity": "medium",
                        "description": f"Activity '{activity.name}' is too short ({activity.duration_minutes} minutes)",
                        "activity": activity.name
                    })
                    score -= 10
                
                if activity.duration_minutes > self.quality_thresholds["maximum_activity_duration"]:
                    issues.append({
                        "type": "too_long_activity",
                        "severity": "medium",
                        "description": f"Activity '{activity.name}' is too long ({activity.duration_minutes} minutes)",
                        "activity": activity.name
                    })
                    score -= 10
        
        # Generate recommendations
        if issues:
            recommendations.append("Adjust activity timing to eliminate overlaps")
            recommendations.append("Ensure realistic travel times between activities")
            recommendations.append("Balance activity durations appropriately")
        
        return {
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations
        }
    
    async def _analyze_budget(self, itinerary: ItineraryDay, user_profile: UserProfile) -> Dict[str, Any]:
        """Analyze budget alignment."""
        issues = []
        recommendations = []
        score = 100
        
        # Get user's budget level
        budget_level = user_profile.budget.level.value
        daily_budget = user_profile.budget.daily_max
        
        # Calculate estimated costs
        estimated_total = 0
        for activity in itinerary.activities:
            if activity.cost:
                estimated_total += activity.cost
            else:
                # Use estimates
                activity_type = activity.type
                if activity_type in self.activity_cost_estimates:
                    estimated_cost = self.activity_cost_estimates[activity_type].get(budget_level, 30)
                    estimated_total += estimated_cost
        
        # Check against daily budget
        if daily_budget and estimated_total > daily_budget:
            over_budget = estimated_total - daily_budget
            issues.append({
                "type": "over_budget",
                "severity": "high",
                "description": f"Estimated cost (${estimated_total:.2f}) exceeds daily budget (${daily_budget:.2f})",
                "over_amount": over_budget
            })
            score -= 30
        
        # Check budget level appropriateness
        expensive_activities = 0
        for activity in itinerary.activities:
            activity_type = activity.type
            if activity_type in self.activity_cost_estimates:
                estimates = self.activity_cost_estimates[activity_type]
                if budget_level == "budget" and activity.cost and activity.cost > estimates["mid-range"]:
                    expensive_activities += 1
                elif budget_level == "luxury" and activity.cost and activity.cost < estimates["mid-range"]:
                    issues.append({
                        "type": "budget_mismatch",
                        "severity": "medium",
                        "description": f"Activity '{activity.name}' may be too budget-oriented for luxury preference",
                        "activity": activity.name
                    })
                    score -= 10
        
        if expensive_activities > 0:
            issues.append({
                "type": "budget_mismatch",
                "severity": "medium",
                "description": f"{expensive_activities} activities may be too expensive for budget preference",
                "count": expensive_activities
            })
            score -= 15
        
        # Generate recommendations
        if issues:
            recommendations.append("Consider adjusting activity choices to match budget")
            recommendations.append("Look for free or low-cost alternatives")
            recommendations.append("Spread expensive activities across multiple days")
        
        return {
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations,
            "estimated_total": estimated_total,
            "daily_budget": daily_budget
        }
    
    async def _analyze_profile_alignment(self, itinerary: ItineraryDay, user_profile: UserProfile) -> Dict[str, Any]:
        """Analyze alignment with user profile."""
        issues = []
        recommendations = []
        score = 100
        
        # Check travel style alignment
        user_styles = [style.value for style in user_profile.preferences.travel_style]
        activity_types = [activity.type.value for activity in itinerary.activities]
        
        style_match = False
        for style in user_styles:
            if style == "cultural" and "cultural" in activity_types:
                style_match = True
            elif style == "adventure" and "outdoor" in activity_types:
                style_match = True
            elif style == "relaxation" and len(activity_types) <= 3:  # Fewer activities = more relaxed
                style_match = True
        
        if not style_match:
            issues.append({
                "type": "style_mismatch",
                "severity": "medium",
                "description": f"Activities don't align with travel style: {', '.join(user_styles)}",
                "user_styles": user_styles,
                "activity_types": activity_types
            })
            score -= 20
        
        # Check pace alignment
        user_pace = user_profile.preferences.pace.value
        activity_count = len(itinerary.activities)
        
        if user_pace == "slow" and activity_count > 4:
            issues.append({
                "type": "pace_mismatch",
                "severity": "medium",
                "description": f"Too many activities ({activity_count}) for slow pace preference",
                "activity_count": activity_count
            })
            score -= 15
        elif user_pace == "fast" and activity_count < 5:
            issues.append({
                "type": "pace_mismatch",
                "severity": "low",
                "description": f"Too few activities ({activity_count}) for fast pace preference",
                "activity_count": activity_count
            })
            score -= 10
        
        # Check interest alignment
        user_interests = [interest.lower() for interest in user_profile.preferences.interests]
        interest_match = False
        
        for activity in itinerary.activities:
            activity_name = activity.name.lower()
            activity_desc = (activity.description or "").lower()
            
            for interest in user_interests:
                if interest in activity_name or interest in activity_desc:
                    interest_match = True
                    break
            
            if interest_match:
                break
        
        if not interest_match and user_interests:
            issues.append({
                "type": "interest_mismatch",
                "severity": "medium",
                "description": f"Activities don't align with user interests: {', '.join(user_interests)}",
                "user_interests": user_interests
            })
            score -= 15
        
        # Check group size appropriateness
        group_size = user_profile.traveler_info.group_size
        if group_size > 4:
            # Check if activities are group-friendly
            for activity in itinerary.activities:
                if activity.type == ActivityType.DINING:
                    # Large groups may need reservations
                    if not activity.booking_reference:
                        issues.append({
                            "type": "group_size_concern",
                            "severity": "low",
                            "description": f"Large group ({group_size}) may need reservations for '{activity.name}'",
                            "activity": activity.name,
                            "group_size": group_size
                        })
                        score -= 5
        
        # Generate recommendations
        if issues:
            recommendations.append("Adjust activities to better match user preferences")
            recommendations.append("Consider user's travel style and interests")
            recommendations.append("Ensure activity count matches preferred pace")
        
        return {
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations
        }
    
    async def _analyze_time_feasibility(self, itinerary: ItineraryDay) -> Dict[str, Any]:
        """Analyze time feasibility of itinerary."""
        issues = []
        recommendations = []
        score = 100
        
        activities = itinerary.activities
        
        if not activities:
            return {"score": 0, "issues": [], "recommendations": []}
        
        # Calculate total day duration
        if activities[0].start_time and activities[-1].end_time:
            total_duration = (activities[-1].end_time - activities[0].start_time).total_seconds() / 60
            
            if total_duration > self.quality_thresholds["reasonable_day_length"]:
                issues.append({
                    "type": "day_too_long",
                    "severity": "medium",
                    "description": f"Day is too long ({total_duration/60:.1f} hours)",
                    "duration_hours": total_duration / 60
                })
                score -= 15
        
        # Calculate travel time ratio
        total_travel_time = sum(
            activity.travel_time_from_previous or 0 
            for activity in activities
        )
        
        total_activity_time = sum(
            activity.duration_minutes or 0 
            for activity in activities
        )
        
        if total_activity_time > 0:
            travel_ratio = total_travel_time / total_activity_time
            
            if travel_ratio > self.quality_thresholds["maximum_travel_time_ratio"]:
                issues.append({
                    "type": "too_much_travel",
                    "severity": "medium",
                    "description": f"Too much time spent traveling ({travel_ratio*100:.1f}%)",
                    "travel_ratio": travel_ratio
                })
                score -= 20
        
        # Check for insufficient breaks
        for i in range(len(activities) - 1):
            current = activities[i]
            next_activity = activities[i + 1]
            
            if current.end_time and next_activity.start_time:
                break_time = (next_activity.start_time - current.end_time).total_seconds() / 60
                travel_time = next_activity.travel_time_from_previous or 0
                actual_break = break_time - travel_time
                
                if actual_break < self.quality_thresholds["minimum_break_time"]:
                    issues.append({
                        "type": "insufficient_break",
                        "severity": "low",
                        "description": f"Insufficient break time between '{current.name}' and '{next_activity.name}'",
                        "break_minutes": actual_break
                    })
                    score -= 5
        
        # Generate recommendations
        if issues:
            recommendations.append("Reduce total day duration")
            recommendations.append("Minimize travel time between activities")
            recommendations.append("Add sufficient break time between activities")
        
        return {
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations
        }
    
    async def _analyze_activity_quality(self, itinerary: ItineraryDay) -> Dict[str, Any]:
        """Analyze quality of individual activities."""
        issues = []
        recommendations = []
        score = 100
        
        activities = itinerary.activities
        
        # Check for activity variety
        activity_types = [activity.type for activity in activities]
        unique_types = set(activity_types)
        
        if len(unique_types) < 2 and len(activities) > 2:
            issues.append({
                "type": "lack_of_variety",
                "severity": "low",
                "description": "Itinerary lacks activity variety",
                "unique_types": len(unique_types),
                "total_activities": len(activities)
            })
            score -= 10
        
        # Check activity ratings
        low_rated_activities = []
        for activity in activities:
            if activity.rating and activity.rating < 3.0:
                low_rated_activities.append(activity.name)
        
        if low_rated_activities:
            issues.append({
                "type": "low_rated_activities",
                "severity": "medium",
                "description": f"Some activities have low ratings: {', '.join(low_rated_activities)}",
                "activities": low_rated_activities
            })
            score -= 15
        
        # Check for essential activities (dining)
        has_dining = any(activity.type == ActivityType.DINING for activity in activities)
        if not has_dining and len(activities) > 2:
            issues.append({
                "type": "missing_dining",
                "severity": "medium",
                "description": "No dining activities planned for the day",
            })
            score -= 15
        
        # Check for location clustering
        if len(activities) > 3:
            # Simple check: if activities are spread across very different locations
            locations = [activity.location for activity in activities if activity.location.latitude]
            if len(locations) > 1:
                # Calculate rough distance spread
                lats = [loc.latitude for loc in locations]
                lngs = [loc.longitude for loc in locations]
                
                lat_spread = max(lats) - min(lats)
                lng_spread = max(lngs) - min(lngs)
                
                # If spread is too large (rough heuristic)
                if lat_spread > 0.1 or lng_spread > 0.1:  # Roughly 10km
                    issues.append({
                        "type": "spread_out_locations",
                        "severity": "low",
                        "description": "Activities are spread across distant locations",
                        "lat_spread": lat_spread,
                        "lng_spread": lng_spread
                    })
                    score -= 10
        
        # Generate recommendations
        if issues:
            recommendations.append("Add variety to activity types")
            recommendations.append("Replace low-rated activities with better alternatives")
            recommendations.append("Include dining options")
            recommendations.append("Group activities by location to reduce travel")
        
        return {
            "score": max(0, score),
            "issues": issues,
            "recommendations": recommendations
        }
    
    async def _analyze_feasibility(self, itinerary: ItineraryDay) -> Dict[str, Any]:
        """Analyze overall feasibility of itinerary."""
        # This is a subset of the comprehensive critique
        logic_result = await self._check_logical_consistency(itinerary)
        time_result = await self._analyze_time_feasibility(itinerary)
        
        return {
            "feasible": len([i for i in logic_result["issues"] + time_result["issues"] if i.get("severity") == "high"]) == 0,
            "logic_issues": logic_result["issues"],
            "time_issues": time_result["issues"],
            "recommendations": logic_result["recommendations"] + time_result["recommendations"]
        }
    
    def _generate_critique_summary(self, score: float, issues: List[Dict[str, Any]], approved: bool) -> str:
        """Generate a summary of the critique."""
        if approved:
            return f"Approved with score {score:.1f}. Ready for user confirmation."
        else:
            high_issues = len([i for i in issues if i.get("severity") == "high"])
            medium_issues = len([i for i in issues if i.get("severity") == "medium"])
            
            return f"Not approved (score {score:.1f}). Found {high_issues} high-priority and {medium_issues} medium-priority issues requiring revision."
    
    async def _generate_detailed_analysis(self, itinerary: ItineraryDay, user_profile: UserProfile, critique_result: CritiqueResult) -> Dict[str, Any]:
        """Generate detailed analysis for logging/debugging."""
        return {
            "itinerary_stats": {
                "total_activities": len(itinerary.activities),
                "activity_types": list(set(a.type.value for a in itinerary.activities)),
                "estimated_duration": sum(a.duration_minutes or 0 for a in itinerary.activities),
                "total_travel_time": sum(a.travel_time_from_previous or 0 for a in itinerary.activities)
            },
            "user_profile_summary": {
                "travel_style": [s.value for s in user_profile.preferences.travel_style],
                "pace": user_profile.preferences.pace.value,
                "budget_level": user_profile.budget.level.value,
                "group_size": user_profile.traveler_info.group_size
            },
            "critique_breakdown": {
                "total_issues": len(critique_result.issues),
                "high_severity": len([i for i in critique_result.issues if i.get("severity") == "high"]),
                "medium_severity": len([i for i in critique_result.issues if i.get("severity") == "medium"]),
                "low_severity": len([i for i in critique_result.issues if i.get("severity") == "low"])
            }
        } 