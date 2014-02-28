import tf
import rospy
import smach

import mir_states.common.basic_states as gbs
import mir_states.common.manipulation_states as gms
import mir_states.common.navigation_states as gns
import mir_states.common.perception_states as gps


__all__ = ['load_object']

class compute_base_shift_to_object(smach.State):
    '''
    MOVED OUT OF LOAD_OBJECT
    '''

    FRAME_ID = '/base_link'

    def __init__(self):
        smach.State.__init__(self,
                             outcomes=['succeeded', 'tf_error'],
                             input_keys=['object'],
                             output_keys=['move_base_by'])
        self.tf_listener = tf.TransformListener()

    def execute(self, userdata):
        pose = userdata.object.pose
        try:
            t = self.tf_listener.getLatestCommonTime(self.FRAME_ID,
                                                     pose.header.frame_id)
            pose.header.stamp = t
            relative = self.tf_listener.transformPose(self.FRAME_ID, pose)
        except (tf.LookupException,
                tf.ConnectivityException,
                tf.ExtrapolationException) as e:
            rospy.logerr('Tf error: %s' % str(e))
            return 'tf_error'
        userdata.move_base_by = (relative.pose.position.x - 0.55, relative.pose.position.y, 0)
        return 'succeeded'

###############################################################################
#                               State machine                                 #
###############################################################################

class load_object(smach.StateMachine):

    def __init__(self):
        smach.StateMachine.__init__(self,
                                    outcomes=['succeeded', 'failed', 'vs_error'],
                                    input_keys=['simulation',
                                                'object',
                                                'rear_platform'],
                                    output_keys=['rear_platform'])
        with self:
            smach.StateMachine.add('OPEN_GRIPPER',
                                   gms.control_gripper('open'),
                                   transitions={'succeeded': 'COMPUTE_BASE_SHIFT_TO_OBJECT'})

            smach.StateMachine.add('COMPUTE_BASE_SHIFT_TO_OBJECT',
                                   compute_base_shift_to_object(),
                                   transitions={'succeeded': 'MOVE_BASE_RELATIVE',
                                                'tf_error': 'failed'})

            smach.StateMachine.add('MOVE_BASE_RELATIVE',
                                   gns.move_base_relative(),
                                   transitions={'succeeded': 'MOVE_ARM_TO_PREGRASP',
                                                'failed': 'failed'})
            '''
            smach.StateMachine.add('AVOID_WALLS_TO_PREGRASP',
                                   gms.move_arm('candle'),
                                   transitions={'succeeded': 'MOVE_ARM_TO_PREGRASP',
                                                'failed': 'failed'})
            
            smach.StateMachine.add('COMPUTE_PREGRASP_POSE',
                                   compute_pregrasp_pose(),
                                   transitions={'succeeded': 'MOVE_ARM_TO_PREGRASP',
                                                'tf_error': 'failed'})

            smach.StateMachine.add('MOVE_ARM_TO_PREGRASP',
                                   gms.move_arm(tolerance=[0, 0.4, 0]),
                                   transitions={'succeeded': 'DO_VISUAL_SERVOING',
                                                'failed': 'COMPUTE_BASE_SHIFT_TO_OBJECT'})
            '''
            smach.StateMachine.add('MOVE_ARM_TO_PREGRASP',
                                   gms.move_arm('pregrasp_laying'),
                                   transitions={'succeeded': 'DO_VISUAL_SERVOING',
                                                'failed': 'failed'})
            
            
            smach.StateMachine.add('DO_VISUAL_SERVOING',
                                   gps.do_visual_servoing(),
                                   transitions={'succeeded': 'GRASP_OBJECT',
                                                'failed': 'failed',
                                                'timeout': 'MOVE_ARM_TO_PREGRASP',
                                                'lost_object': 'VISUAL_SERVOING_LOST'})

            smach.StateMachine.add('VISUAL_SERVOING_LOST',
                                  gbs.loop_for(4),
                                  transitions={'loop': 'MOVE_ARM_TO_PREGRASP',
                                               'continue': 'vs_error'})
            
            smach.StateMachine.add('GRASP_OBJECT',
                                   gms.grasp_object(),
                                   transitions={'succeeded': 'PUT_OBJECT_ON_REAR_PLATFORM',
                                                'tf_error': 'failed'})
            '''
            smach.StateMachine.add('AVOID_WALLS_FROM_PLATFORM',
                                   gms.move_arm('pregrasp_laying'),
                                   transitions={'succeeded': 'PUT_OBJECT_ON_REAR_PLATFORM',
                                                'failed': 'failed'})
            '''
            smach.StateMachine.add('PUT_OBJECT_ON_REAR_PLATFORM',
                                   gms.put_object_on_rear_platform(),
                                   transitions={'succeeded': 'succeeded',
                                                'rear_platform_is_full': 'failed',
                                                'failed': 'failed'})

            smach.StateMachine.add('RECOVERY_STOW_ARM', gms.move_arm('candle'),
                                   transitions={'succeeded': 'COMPUTE_BASE_SHIFT_TO_OBJECT',
                                                'failed': 'RECOVERY_STOW_ARM'})

