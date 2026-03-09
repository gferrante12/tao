// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldISimEventdIsrcdISimTVTHitDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimTVTHit.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLSimTVTHit(void *p = nullptr);
   static void *newArray_TaocLcLSimTVTHit(Long_t size, void *p);
   static void delete_TaocLcLSimTVTHit(void *p);
   static void deleteArray_TaocLcLSimTVTHit(void *p);
   static void destruct_TaocLcLSimTVTHit(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::SimTVTHit*)
   {
      ::Tao::SimTVTHit *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::SimTVTHit >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::SimTVTHit", ::Tao::SimTVTHit::Class_Version(), "Event/SimTVTHit.h", 10,
                  typeid(::Tao::SimTVTHit), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::SimTVTHit::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::SimTVTHit) );
      instance.SetNew(&new_TaocLcLSimTVTHit);
      instance.SetNewArray(&newArray_TaocLcLSimTVTHit);
      instance.SetDelete(&delete_TaocLcLSimTVTHit);
      instance.SetDeleteArray(&deleteArray_TaocLcLSimTVTHit);
      instance.SetDestructor(&destruct_TaocLcLSimTVTHit);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::SimTVTHit*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::SimTVTHit*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::SimTVTHit*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr SimTVTHit::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *SimTVTHit::Class_Name()
{
   return "Tao::SimTVTHit";
}

//______________________________________________________________________________
const char *SimTVTHit::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimTVTHit*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int SimTVTHit::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimTVTHit*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *SimTVTHit::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimTVTHit*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *SimTVTHit::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimTVTHit*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void SimTVTHit::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::SimTVTHit.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::SimTVTHit::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::SimTVTHit::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLSimTVTHit(void *p) {
      return  p ? new(p) ::Tao::SimTVTHit : new ::Tao::SimTVTHit;
   }
   static void *newArray_TaocLcLSimTVTHit(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::SimTVTHit[nElements] : new ::Tao::SimTVTHit[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLSimTVTHit(void *p) {
      delete (static_cast<::Tao::SimTVTHit*>(p));
   }
   static void deleteArray_TaocLcLSimTVTHit(void *p) {
      delete [] (static_cast<::Tao::SimTVTHit*>(p));
   }
   static void destruct_TaocLcLSimTVTHit(void *p) {
      typedef ::Tao::SimTVTHit current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::SimTVTHit

namespace ROOT {
   static TClass *vectorlETaocLcLSimTVTHitgR_Dictionary();
   static void vectorlETaocLcLSimTVTHitgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLSimTVTHitgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLSimTVTHitgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLSimTVTHitgR(void *p);
   static void deleteArray_vectorlETaocLcLSimTVTHitgR(void *p);
   static void destruct_vectorlETaocLcLSimTVTHitgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::SimTVTHit>*)
   {
      vector<Tao::SimTVTHit> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::SimTVTHit>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::SimTVTHit>", -2, "vector", 389,
                  typeid(vector<Tao::SimTVTHit>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLSimTVTHitgR_Dictionary, isa_proxy, 4,
                  sizeof(vector<Tao::SimTVTHit>) );
      instance.SetNew(&new_vectorlETaocLcLSimTVTHitgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLSimTVTHitgR);
      instance.SetDelete(&delete_vectorlETaocLcLSimTVTHitgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLSimTVTHitgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLSimTVTHitgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::SimTVTHit> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::SimTVTHit>","std::vector<Tao::SimTVTHit, std::allocator<Tao::SimTVTHit> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::SimTVTHit>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLSimTVTHitgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::SimTVTHit>*>(nullptr))->GetClass();
      vectorlETaocLcLSimTVTHitgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLSimTVTHitgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLSimTVTHitgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimTVTHit> : new vector<Tao::SimTVTHit>;
   }
   static void *newArray_vectorlETaocLcLSimTVTHitgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimTVTHit>[nElements] : new vector<Tao::SimTVTHit>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLSimTVTHitgR(void *p) {
      delete (static_cast<vector<Tao::SimTVTHit>*>(p));
   }
   static void deleteArray_vectorlETaocLcLSimTVTHitgR(void *p) {
      delete [] (static_cast<vector<Tao::SimTVTHit>*>(p));
   }
   static void destruct_vectorlETaocLcLSimTVTHitgR(void *p) {
      typedef vector<Tao::SimTVTHit> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::SimTVTHit>

namespace {
  void TriggerDictionaryInitialization_SimTVTHitDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimTVTHit.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/SimEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/SimEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "SimTVTHitDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimTVTHit.h")))  SimTVTHit;}
namespace std{template <typename _Tp> class __attribute__((annotate("$clingAutoload$bits/allocator.h")))  __attribute__((annotate("$clingAutoload$string")))  allocator;
}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "SimTVTHitDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimTVTHit.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::SimTVTHit", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("SimTVTHitDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_SimTVTHitDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_SimTVTHitDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_SimTVTHitDict() {
  TriggerDictionaryInitialization_SimTVTHitDict_Impl();
}
