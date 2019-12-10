---
title: Job Submission Generator
---
<script src="https://code.angularjs.org/1.7.9/angular.js"></script>
<script src="https://code.angularjs.org/1.7.9/angular-messages.js"></script>

!!!info "Automatic parameter selection"
    - You can manually specify parameters at job submission using the command below. If needed, all parameters [can also be automatically configured at queue level](../tutorials/integration-ec2-job-parameters/#how-to-use-custom-parameters). 
    - Job will use the default parameters configured for its queue unless the parameter is explicitely specified during submission (**job parameters override queue parameters**),
    - [Refer to this page](../tutorials/launch-your-first-job/#examples) for examples.
    

<body ng-app="myApp">
<div ng-controller="myCtrl">

<style>
* {
  box-sizing: border-box;
}

.input2 {

width: 100%;
  padding: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  resize: vertical;
}


.container {
  border-radius: 5px;
  background-color: #f2f2f2;
  padding: 5px;
}

.col-25 {
  float: left;
  width: 25%;
  margin-top: 6px;
}

.col-75 {
  float: left;
  width: 75%;
  margin-top: 6px;
}

/* Clear floats after the columns */
.row:after {
  content: "";
  display: table;
  clear: both;
}

/* Responsive layout - when the screen is less than 600px wide, make the two columns stack on top of each other instead of next to each other */
@media screen and (max-width: 600px) {
  .col-25, .col-75, input[type=submit] {
    width: 100%;
    margin-top: 0;
  }
}


.md-content {
margin-right: 0;
}

</style>






<div class="container">



<h2> Your Command </h2>
<strong>user@host:</strong> qsub {{qsub_instance_ami}} 
{{qsub_instance_type}} 
{{qsub_subnet_id}} 
{{qsub_spot_price}}
{{qsub_efa_support}}
{{qsub_placement_group}}
{{qsub_root_size}}
{{qsub_scratch_size}}
{{qsub_scratch_iops}}
{{qsub_fsx_lustre_bucket}}
{{qsub_fsx_lustre_size}}
{{qsub_fsx_lustre_dns}}
{{qsub_ht_support}}
{{qsub_spot_allocation_count}}
{{qsub_spot_allocation_strategy}}
{{qsub_nodes}}
{{qsub_base_os}}
myscript.sh

<h2> Job Parameters</h2>

<form name="QsubForm">

<h3> Compute parameters: </h3>

   <input class="input2" name="nodes" size="35" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="nodes" placeholder="Number of nodes to provision for your simulation" pattern="\d+"/>
      <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#nodes">Documentation</a></i>
    <div ng-messages="QsubForm.nodes.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Must be a number</div>
   </div>

   <input class="input2" required name="instance_ami" size="35" ng-minlength="3" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="instance_ami" placeholder="Specify your instance AMI" pattern="^ami-[a-zA-Z0-9]*" />
   <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#instance_ami">Documentation</a></i>
   <div ng-messages="QsubForm.instance_ami.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Image name must start with "ami-"</div>
   </div>
   
   <input class="input2" required name="base_os" size="35" ng-minlength="3" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="base_os" placeholder="Specify the base os of your AMI (default to OS selected during installation)" pattern="centos7|rhel7|amazonlinux2" />
   <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#base_os">Documentation</a></i>

   <div ng-messages="QsubForm.base_os.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Must be centos7, rhel7 or amazonlinux2</div>
   </div>
   
   <input class="input2"  size="35" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="instance_type" placeholder="Specify your instance type (use + to specify more than one eg. c5.large+m5.large)" />
   <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#instance_type">Documentation</a></i>
   
   <input class="input2"  name="subnet_id" size="35" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="subnet_id" placeholder="Specify your subnet id" pattern="^sub-[a-zA-Z0-9]*" />
      <i><a style="padding: 5px"target="_blank"  href="../tutorials/integration-ec2-job-parameters/#subnet_id">Documentation</a></i>
    <div ng-messages="QsubForm.subnet_id.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Subnet name must start with "sub-"</div>
   </div>
   
   <input class="input2"  name="spot_price" size="35" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="spot_price" placeholder="Specify your maximum spot price (use auto to match OD price)" pattern="[+-]?([0-9]*[.])?[0-9]+|auto"/>
   <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#spot_price">Documentation</a></i>

   <div ng-messages="QsubForm.spot_price.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Spot Price must be a float (eg 1.2) or auto</div>
   </div>
   
   <input class="input2"  name="spot_allocation_count" size="35" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="spot_allocation_count" placeholder="Specify the number of SPOT instances to provision when using mixed OD and SPOT" />
   <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#spot_allocation_count">Documentation</a></i>

   <div ng-messages="QsubForm.spot_allocation_count.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Spot Price must be a float (eg 1.2)</div>
   </div>
   
   <input class="input2"  name="spot_allocation_strategy" size="35" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="spot_allocation_strategy" placeholder="SPOT allocation strategy: lowest-cost (default)  or capacity-optimized" pattern="lowest-cost|capacity-optimized"/>
      <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#spot_allocation_strategy">Documentation</a></i>
   <div ng-messages="QsubForm.spot_allocation_strategy.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Must be either lowest-cost or capacity-optimized</div>
   </div>

    
<h3> Storage parameters: </h3>   
   
   
   <input class="input2"  name="root_size" size="35"  style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="root_size" placeholder="Size of the root partition (in GB)"  pattern="\d+" />
      <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#root_size">Documentation</a></i>

   <div ng-messages="QsubForm.root_size.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Root Size must be a number</div>
   </div>
   
   <input class="input2"  name="scratch_size" size="35"  style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="scratch_size" placeholder="Size of the scratch partition (in GB)" pattern="\d+"/>
      <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#scratch_size">Documentation</a></i>

   <div ng-messages="QsubForm.scratch_size.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Scratch Size must be a number</div>
   </div>
   
  
   <input class="input2"  size="50" name = "scratch_iops" style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="scratch_iops" placeholder="IOPS to be provisioned for scratch partition (will automatically provision io1 EBS if specified)" pattern="\d+" />
       <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#scratch_iops">Documentation</a></i>

   <div ng-messages="QsubForm.scratch_iops.$error">
        <div style="color: red; font-size: medium" ng-message="pattern">Provisioned IO/s must be a number</div>
   </div>
   
   
   <input class="input2"  size="35"  style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="fsx_lustre_bucket" placeholder="Specify S3 bucket name to mount using FSx for Lustre (will create a new one)" />
      <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#fsx_lustre_bucket">Documentation</a></i>

   <input class="input2"  size="35"  style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="fsx_lustre_size" placeholder="Size of the FSx partition (in GB)" />
      <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#fsx_lustre_size">Documentation</a></i>

   <input class="input2"  size="35"  style="font-size: 15px;  margin-top: 6px;" type="text" ng-change="myFunc()" ng-model="fsx_lustre_dns" placeholder="Specify an existing FSx to mount on all nodes" />
      <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#fsx_lustre_dns">Documentation</a></i>


<h3>Flags: </h3>
   <input type="checkbox" ng-change="myFunc()" ng-model="efa_support"> I want to use EFA <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#efa_support">Documentation</a></i> <br>
   <input type="checkbox" ng-change="myFunc()" ng-model="placement_group"> I do not want to use Placement Group (enabled by default)    <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#placement_group">Documentation</a></i> <br>
   <input type="checkbox" ng-change="myFunc()" ng-model="ht_support"> I want to enable HyperThreading (disabled by default)   <i><a style="padding: 5px" target="_blank" href="../tutorials/integration-ec2-job-parameters/#ht_support">Documentation</a></i><br>

</form> 
  

</div>

<script>
  angular.module('myApp', ['ngMessages'])
    .controller('myCtrl', ['$scope', function($scope) {
      $scope.count = 0;
      $scope.myFunc = function() {
        if($scope.nodes){$scope.qsub_nodes = "-l nodes=" + $scope.nodes;}else{$scope.qsub_nodes = "";}
        if($scope.instance_ami){$scope.qsub_instance_ami = "-l instance_ami=" + $scope.instance_ami;}else{$scope.qsub_instance_ami = "";}
        if($scope.base_os){$scope.qsub_base_os = "-l base_os=" + $scope.base_os;}else{$scope.qsub_base_os = "";}

        if($scope.instance_type){$scope.qsub_instance_type = "-l instance_type=" + $scope.instance_type;}else{$scope.qsub_instance_type = "";}
        if($scope.subnet_id){$scope.qsub_subnet_id = "-l subnet_id=" + $scope.subnet_id;}else{$scope.qsub_subnet_id = "";}
        if($scope.spot_price){$scope.qsub_spot_price = "-l spot_price=" + $scope.spot_price;}else{$scope.qsub_spot_price= "";}
        if($scope.root_size){$scope.qsub_root_size= "-l root_size=" + $scope.root_size;}else{$scope.qsub_root_size= "";}
        if($scope.scratch_size){$scope.qsub_scratch_size = "-l scratch_size=" + $scope.scratch_size;}else{$scope.qsub_scratch_size= "";}
        if($scope.scratch_iops){$scope.qsub_scratch_iops= "-l scratch_iops=" + $scope.scratch_iops;}else{$scope.qsub_scratch_iops= "";}     
        if($scope.spot_allocation_count){$scope.qsub_spot_allocation_count= "-l spot_allocation_acount=" + $scope.spot_allocation_count;}else{$scope.qsub_spot_allocation_count= "";}     
        if($scope.spot_allocation_strategy){$scope.qsub_spot_allocation_strategy= "-l spot_allocation_strategy=" + $scope.spot_allocation_strategy;}else{$scope.qsub_spot_allocation_strategy= "";}     

        
        
        if($scope.efa_support){$scope.qsub_efa_support = "-l efa_support=True";}else{$scope.qsub_efa_support= "";}
        if($scope.placement_group){$scope.qsub_placement_group = "-l placement_group=False";}else{$scope.qsub_placement_group= "";}
        if($scope.ht_support){$scope.qsub_ht_support = "-l ht_support=True";}else{$scope.qsub_ht_support= "";}

        
        if($scope.fsx_lustre_bucket){$scope.qsub_fsx_lustre_bucket = "-l fsx_lustre_bucket=" + $scope.fsx_lustre_bucket;}else{$scope.qsub_fsx_lustre_bucket = "";}
        if($scope.fsx_lustre_size){$scope.qsub_fsx_lustre_size = "-l fsx_lustre_size=" + $scope.fsx_lustre_size;}else{$scope.qsub_fsx_lustre_size = "";}
        if($scope.fsx_lustre_dns){$scope.qsub_fsx_lustre_dns = "-l fsx_lustre_dnst=" + $scope.fsx_lustre_dns;}else{$scope.qsub_fsx_lustre_dns = "";}

      
      };
    }]);
</script>




</body>

